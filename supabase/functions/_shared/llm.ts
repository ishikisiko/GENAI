interface ChatJsonOptions {
  prompt: string;
  temperature?: number;
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

function getEnv(name: string): string | undefined {
  const value = Deno.env.get(name)?.trim();
  return value ? value : undefined;
}

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
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

export async function chatJson({ prompt, temperature = 0.7 }: ChatJsonOptions) {
  const { apiKey, model, baseUrl, provider } = getLlmConfig();

  if (!apiKey) {
    throw new Error("LLM_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY is not configured");
  }

  const response = provider === "anthropic"
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
          model,
          max_tokens: Number(getEnv("LLM_MAX_TOKENS") || 4096),
          messages: [{ role: "user", content: prompt }],
          temperature,
        }),
      })
    : await fetch(`${baseUrl}/chat/completions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model,
          messages: [{ role: "user", content: prompt }],
          temperature,
          response_format: { type: "json_object" },
        }),
      });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`LLM API error: ${errorText}`);
  }

  const content = provider === "anthropic"
    ? ((await response.json() as AnthropicMessageResponse).content || [])
        .filter((item) => item.type === "text")
        .map((item) => item.text || "")
        .join("")
    : ((await response.json() as ChatCompletionResponse).choices?.[0]?.message?.content || "");

  if (!content) {
    throw new Error("LLM returned an empty response");
  }

  return JSON.parse(content);
}
