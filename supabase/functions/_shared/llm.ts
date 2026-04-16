interface ChatJsonOptions {
  prompt: string;
  temperature?: number;
  maxRetries?: number;
}

interface ChatCompletionResponse {
  choices?: Array<{
    message?: {
      content?: string;
    };
  }>;
}

interface AnthropicMessageResponse {
  content?: Array<{
    type?: string;
    text?: string;
  }>;
}

type LlmErrorMeta = {
  status?: number;
  statusText?: string;
  rawText?: string;
  parsedPayload?: unknown;
  promptLength?: number;
};

function getEnv(name: string): string | undefined {
  const value = Deno.env.get(name)?.trim();
  return value ? value : undefined;
}

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function createTimeoutController(timeoutMs: number): { signal: AbortSignal; clear: () => void } {
  const controller = new AbortController();
  const timer = setTimeout(() => {
    controller.abort(`LLM request timed out after ${timeoutMs}ms`);
  }, timeoutMs);

  return {
    signal: controller.signal,
    clear: () => clearTimeout(timer),
  };
}

function extractJsonCandidates(content: string): string[] {
  const candidates: string[] = [];
  const seen = new Set<string>();
  const add = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) return;
    if (seen.has(trimmed)) return;
    seen.add(trimmed);
    candidates.push(trimmed);
  };

  const trimmed = content.trim();
  add(trimmed);

  const fencedMatch = /^```(?:json)?\s*([\s\S]*?)\s*```$/i;
  const fullMatch = trimmed.match(fencedMatch);
  if (fullMatch?.[1]) {
    add(fullMatch[1]);
  }

  const fenceRegex = /```(?:json)?\s*([\s\S]*?)\s*```/gi;
  let fenceMatch: RegExpExecArray | null;
  while ((fenceMatch = fenceRegex.exec(content)) !== null) {
    if (fenceMatch[1]) {
      add(fenceMatch[1]);
    }
  }

  const stack: string[] = [];
  let start = -1;
  let inString = false;
  let escaped = false;
  for (let i = 0; i < content.length; i++) {
    const char = content[i];
    if (escaped) {
      escaped = false;
      continue;
    }
    if (char === "\\") {
      if (inString) escaped = true;
      continue;
    }
    if (char === "\"") {
      inString = !inString;
      continue;
    }
    if (inString) continue;

    if (char === "{" || char === "[") {
      if (stack.length === 0) {
        start = i;
      }
      stack.push(char === "{" ? "}" : "]");
      continue;
    }

    if ((char === "}" || char === "]") && stack.length > 0 && char === stack[stack.length - 1]) {
      stack.pop();
      if (stack.length === 0 && start >= 0) {
        add(content.slice(start, i + 1));
        start = -1;
      }
    }
  }

  return candidates;
}

function getAnthropicMessagesUrl(baseUrl: string): string {
  return baseUrl.endsWith("/v1") ? `${baseUrl}/messages` : `${baseUrl}/v1/messages`;
}

export function getLlmConfig() {
  const apiKey = getEnv("LLM_API_KEY") || getEnv("ANTHROPIC_API_KEY") || getEnv("OPENAI_API_KEY");
  const model = getEnv("LLM_MODEL") || getEnv("ANTHROPIC_MODEL") || "gpt-4o-mini";
  const baseUrl = trimTrailingSlash(
    getEnv("LLM_BASE_URL") || getEnv("ANTHROPIC_BASE_URL") || "https://api.openai.com/v1"
  );
  const provider = getEnv("LLM_PROVIDER")
    || (baseUrl.includes("/anthropic") || baseUrl.includes("anthropic") ? "anthropic" : "openai");

  return { apiKey, model, baseUrl, provider };
}

function isRetryableError(status: number, errorText: string): boolean {
  if (status === 429 || status === 500 || status === 502 || status === 503 || status === 504 || status === 529) {
    return true;
  }
  return errorText.includes("overloaded_error");
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function extractJsonString(content: string): string {
  const candidates = extractJsonCandidates(content);
  for (const candidate of candidates) {
    try {
      JSON.parse(candidate);
      return candidate;
    } catch {
      // keep trying other candidates
    }
  }
  throw new Error("LLM returned non-JSON content");
}

async function requestJson(prompt: string, temperature: number) {
  const { apiKey, model, baseUrl, provider } = getLlmConfig();
  const timeoutMs = Number(getEnv("LLM_REQUEST_TIMEOUT_MS") || "120000");

  if (!apiKey) {
    throw new Error("LLM_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY is not configured");
  }

  const requestConfig = {
    model,
    temperature,
    max_tokens: Number(getEnv("LLM_MAX_TOKENS") || 4096),
    messages: [{ role: "user", content: prompt }],
  };
  const { signal, clear } = createTimeoutController(Number.isFinite(timeoutMs) ? timeoutMs : 120000);

  let response: Response;
  try {
    response = provider === "anthropic"
      ? await fetch(getAnthropicMessagesUrl(baseUrl), {
          // Anthropic-compatible providers often use a base URL like
          // https://api.minimaxi.com/anthropic and expose the actual endpoint at /v1/messages.
          // Normalize that here so callers only configure the provider base once.
          method: "POST",
          headers: {
            "x-api-key": apiKey,
            "anthropic-version": getEnv("ANTHROPIC_VERSION") || "2023-06-01",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            ...requestConfig,
            max_tokens: Number(getEnv("LLM_MAX_TOKENS") || 4096),
          }),
          signal,
        })
      : await fetch(`${baseUrl}/chat/completions`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${apiKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            ...requestConfig,
            response_format: { type: "json_object" },
          }),
          signal,
        });
  } catch (error) {
    clear();
    const timeoutMessage = error instanceof Error ? error.message : String(error);
    const isTimeout = timeoutMessage.includes("timed out") || (error instanceof DOMException && error.name === "AbortError");
    const meta = {
      status: 0,
      statusText: isTimeout ? "Request timed out" : (error instanceof Error ? error.message : "Request error"),
      promptLength: prompt.length,
    };
    console.error(`[LLM] Request failed for ${provider}/${model} at ${baseUrl}`, meta, error);
    throw Object.assign(new Error(isTimeout ? "LLM request timeout" : "LLM request failed"), {
      status: 0,
      retryable: true,
      ...meta,
    });
  }

  clear();

  const promptLength = prompt.length;
  let rawText = "";
  try {
    rawText = await response.text();
  } catch (error) {
    const meta: LlmErrorMeta = {
      status: response.status,
      statusText: response.statusText,
      rawText: "",
      promptLength,
    };
    console.error(`[LLM] Failed to read response body for ${provider}/${model} at ${baseUrl}`, meta, error);
    throw Object.assign(new Error("LLM_API_READ_ERROR"), {
      status: response.status,
      retryable: true,
      ...meta,
    });
  }

  if (!response.ok) {
    const meta: LlmErrorMeta = {
      status: response.status,
      statusText: response.statusText,
      rawText,
      promptLength,
    };
    console.error(`[LLM] Non-OK response for ${provider}/${model} at ${baseUrl}`, meta, `\nrawText:\n${rawText}`);
    throw Object.assign(new Error(`LLM API error: ${rawText}`), {
      status: response.status,
      retryable: isRetryableError(response.status, rawText),
      ...meta,
    });
  }

  let parsedPayload: unknown;
  try {
    parsedPayload = JSON.parse(rawText);
  } catch (error) {
    const meta: LlmErrorMeta = {
      status: response.status,
      statusText: response.statusText,
      rawText,
      promptLength,
    };
    console.error(`[LLM] Failed to parse top-level JSON for ${provider}/${model} at ${baseUrl}`, meta, `\nrawText:\n${rawText}`, error);
    throw Object.assign(new Error("LLM returned invalid JSON response"), {
      status: response.status,
      retryable: isRetryableError(response.status, rawText),
      ...meta,
    });
  }

  const content = provider === "anthropic"
    ? ((parsedPayload as AnthropicMessageResponse).content || [])
        .filter((item) => item.type === "text")
        .map((item) => item.text || "")
        .join("")
    : ((parsedPayload as ChatCompletionResponse).choices?.[0]?.message?.content || "");

  if (!content) {
    const meta: LlmErrorMeta = {
      status: response.status,
      statusText: response.statusText,
      rawText,
      parsedPayload,
      promptLength,
    };
    console.error(`[LLM] Empty response content for ${provider}/${model} at ${baseUrl}`, meta, `\nrawText:\n${rawText}`, `\nparsedPayload:\n${JSON.stringify(parsedPayload)}`);
    throw Object.assign(new Error("LLM returned an empty response"), {
      status: response.status,
      retryable: true,
      ...meta,
    });
  }

  try {
    const extracted = extractJsonString(content);
    return JSON.parse(extracted);
  } catch (error) {
    const candidates = extractJsonCandidates(content);
    const meta: LlmErrorMeta = {
      status: response.status,
      statusText: response.statusText,
      rawText,
      parsedPayload,
      promptLength,
    };
    console.error(
      `[LLM] Failed to parse extracted content for ${provider}/${model} at ${baseUrl}`,
      meta,
      `\nrawText:\n${rawText}`,
      `\ncandidates:\n${candidates.join("\n---\n")}`,
      error
    );
    throw Object.assign(new Error("LLM returned non-JSON content"), {
      status: response.status,
      retryable: isRetryableError(response.status, rawText),
      ...meta,
    });
  }
}

export async function chatJson({ prompt, temperature = 0.7, maxRetries = 2 }: ChatJsonOptions) {
  let attempt = 0;
  let lastError: unknown;

  while (attempt <= maxRetries) {
    try {
      return await requestJson(prompt, temperature);
    } catch (error) {
      lastError = error;
      const retryable = typeof error === "object" && error !== null && "retryable" in error && Boolean(error.retryable);
      if (!retryable || attempt === maxRetries) {
        throw error;
      }
      await sleep(1000 * (2 ** attempt));
      attempt += 1;
    }
  }

  throw lastError instanceof Error ? lastError : new Error("Unknown LLM error");
}
