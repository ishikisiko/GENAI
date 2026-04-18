import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";
import { chatJson, getLlmConfig } from "../_shared/llm.ts";

// Compatibility-only rollback shim. The primary product path is POST /api/simulations.

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey",
};

interface RunSimulationRequest {
  case_id: string;
  run_type: "baseline" | "intervention";
  total_rounds: number;
  strategy_type?: string;
  strategy_message?: string;
  injection_round?: number;
}

const ALLOWED_STRATEGIES = ["apology", "clarification", "compensation", "rebuttal"] as const;
type AllowedStrategyType = (typeof ALLOWED_STRATEGIES)[number];
const DEFAULT_STALE_RUN_TIMEOUT_MS = 20 * 60 * 1000;

type RunningSimulationRecord = {
  id: string;
  created_at: string | null;
  last_heartbeat_at?: string | null;
};

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

function formatRoundLog(round: number, case_id: string, run_id: string | null, run_type: string, strategy_type?: string) {
  return {
    round,
    case_id,
    run_id,
    run_type,
    strategy_type: strategy_type ?? "baseline",
  };
}

function getStaleRunTimeoutMs() {
  const raw = Number(Deno.env.get("SIMULATION_STALE_RUN_TIMEOUT_MS") || DEFAULT_STALE_RUN_TIMEOUT_MS);
  return Number.isFinite(raw) && raw > 0 ? raw : DEFAULT_STALE_RUN_TIMEOUT_MS;
}

function getRunHeartbeatTime(run: RunningSimulationRecord) {
  const timestamp = run.last_heartbeat_at || run.created_at;
  return timestamp ? Date.parse(timestamp) : Number.NaN;
}

function isRunStale(run: RunningSimulationRecord, staleBeforeMs: number) {
  const heartbeatTime = getRunHeartbeatTime(run);
  return Number.isFinite(heartbeatTime) && heartbeatTime < staleBeforeMs;
}

async function updateRunHeartbeat(
  supabase: ReturnType<typeof createClient>,
  runId: string,
  updates: Record<string, unknown> = {},
) {
  const payload = {
    last_heartbeat_at: new Date().toISOString(),
    ...updates,
  };
  const { error } = await supabase
    .from("simulation_runs")
    .update(payload)
    .eq("id", runId);
  if (error) {
    console.error("Failed to update simulation heartbeat", { runId, error: error.message, updates });
  }
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 200, headers: corsHeaders });
  }

  let run_id: string | null = null;

  try {
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const body: RunSimulationRequest = await req.json();
    const {
      case_id,
      run_type,
      total_rounds: rawTotalRounds,
      strategy_type,
      strategy_message,
      injection_round,
    } = body;
    if (run_type !== "baseline" && run_type !== "intervention") {
      return new Response(
        JSON.stringify({ error: "run_type must be 'baseline' or 'intervention'" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }
    const total_rounds = Math.min(Math.max(Number.isFinite(rawTotalRounds) ? Number(rawTotalRounds) : 5, 1), 20);
    const normalizedStrategyType = strategy_type?.toLowerCase() as AllowedStrategyType | undefined;
    const normalizedInjectionRound = run_type === "intervention"
      ? Math.min(Math.max(Number.isFinite(injection_round) ? Number(injection_round) : 1, 1), total_rounds)
      : null;

    if (run_type === "intervention") {
      if (!normalizedStrategyType) {
        return new Response(
          JSON.stringify({ error: "strategy_type is required for intervention runs" }),
          { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      if (!ALLOWED_STRATEGIES.includes(normalizedStrategyType)) {
        return new Response(
          JSON.stringify({ error: "invalid strategy_type. Allowed values: apology, clarification, compensation, rebuttal" }),
          { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
    }

    if (!case_id) {
      return new Response(
        JSON.stringify({ error: "case_id is required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { apiKey } = getLlmConfig();
    if (!apiKey) {
      return new Response(
        JSON.stringify({ error: "LLM_API_KEY or OPENAI_API_KEY not configured" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const [agentsResult, claimsResult, entitiesResult, caseResult] = await Promise.all([
      supabase.from("agent_profiles").select("*").eq("case_id", case_id),
      supabase.from("claims").select("*").eq("case_id", case_id),
      supabase.from("entities").select("*").eq("case_id", case_id),
      supabase.from("crisis_cases").select("*").eq("id", case_id).maybeSingle(),
    ]);
    const queryError = agentsResult.error || claimsResult.error || entitiesResult.error || caseResult.error;
    if (queryError) {
      console.error("Failed to load case context for simulation", {
        case_id,
        queryError: queryError.message,
        agents_error: agentsResult.error?.message,
        claims_error: claimsResult.error?.message,
        entities_error: entitiesResult.error?.message,
        case_error: caseResult.error?.message,
      });
      return new Response(
        JSON.stringify({ error: `Failed to load case context: ${queryError.message}` }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { data: agents } = agentsResult;
    const { data: claims } = claimsResult;
    const { data: entities } = entitiesResult;
    const { data: caseData } = caseResult;

    if (!caseData) {
      return new Response(
        JSON.stringify({ error: "Case not found" }),
        { status: 404, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    if (!agents || agents.length === 0) {
      return new Response(
        JSON.stringify({ error: "No agents found for this case. Generate agents first." }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { data: runningRuns, error: runningRunsErr } = await supabase
      .from("simulation_runs")
      .select("id, created_at, last_heartbeat_at")
      .eq("case_id", case_id)
      .eq("status", "running");
    if (runningRunsErr) {
      console.error("Failed to check running simulations", {
        case_id,
        error: runningRunsErr.message,
      });
      return new Response(
        JSON.stringify({ error: `Failed to check running simulations: ${runningRunsErr.message}` }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }
    const staleBeforeMs = Date.now() - getStaleRunTimeoutMs();
    const staleRunningRuns = (runningRuns || []).filter((run) => isRunStale(run as RunningSimulationRecord, staleBeforeMs));
    if (staleRunningRuns.length > 0) {
      const staleIds = staleRunningRuns.map((run) => run.id);
      const { error: staleUpdateErr } = await supabase
        .from("simulation_runs")
        .update({
          status: "failed",
          error_message: "Simulation was interrupted or timed out before completion.",
          completed_at: new Date().toISOString(),
          last_heartbeat_at: new Date().toISOString(),
        })
        .in("id", staleIds);
      if (staleUpdateErr) {
        console.error("Failed to expire stale running simulations", {
          case_id,
          staleIds,
          error: staleUpdateErr.message,
        });
      } else {
        console.warn("Expired stale running simulations", { case_id, staleIds });
      }
    }

    const activeRunningRuns = (runningRuns || []).filter((run) => !isRunStale(run as RunningSimulationRecord, staleBeforeMs));
    if (activeRunningRuns.length > 0) {
      return new Response(
        JSON.stringify({ error: "Another simulation is already running for this case. Please wait until it finishes." }),
        { status: 409, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { data: run } = await supabase
      .from("simulation_runs")
      .insert({
        case_id,
        run_type,
        strategy_type: normalizedStrategyType || null,
        strategy_message: strategy_message || null,
        injection_round: normalizedInjectionRound,
        total_rounds,
        status: "running",
        last_heartbeat_at: new Date().toISOString(),
      })
      .select()
      .maybeSingle();

    if (!run) {
      return new Response(
        JSON.stringify({ error: "Failed to create simulation run" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    run_id = run.id;

    const crisisContext = `
Crisis: ${(caseData as { title?: string } | null)?.title || "Unknown Crisis"}

Key Facts:
${(claims || []).slice(0, 8).map((c: { claim_type: string; content: string }) => `- [${c.claim_type}] ${c.content}`).join("\n")}

Key Entities: ${(entities || []).map((e: { name: string; entity_type: string }) => `${e.name} (${e.entity_type})`).join(", ")}
`;

    const agentSummaries = (agents || []).map((a: {
      id: string; role: string; stance: string; concern: string;
      emotional_sensitivity: number; spread_tendency: number;
      persona_description: string; initial_beliefs: string[];
    }) =>
      `${a.role.toUpperCase()} - ${a.persona_description}\nStance: ${a.stance}\nConcern: ${a.concern}\nEmotional Sensitivity: ${a.emotional_sensitivity}/10, Spread Tendency: ${a.spread_tendency}/10\nBeliefs: ${(a.initial_beliefs || []).join("; ")}`
    ).join("\n\n");

    let previousNarrative = "The crisis has just emerged publicly. Initial reactions are forming.";
    let previousSentiment = -0.3;

    for (let round = 1; round <= total_rounds; round++) {
      await updateRunHeartbeat(supabase, run_id, { status: "running" });

      const isInjectionRound = run_type === "intervention" && normalizedInjectionRound !== null && round === normalizedInjectionRound;
      const strategyApplied = isInjectionRound ? normalizedStrategyType : null;

      const strategyContext = isInjectionRound
        ? `\n\nCRISIS RESPONSE STRATEGY INJECTED (Round ${round}):
Strategy Type: ${normalizedStrategyType?.toUpperCase()}
Message: "${strategy_message || getDefaultStrategyMessage(normalizedStrategyType || "")}"
This response has just been made public. All agents are now aware of this official response.`
        : (run_type === "intervention" && normalizedInjectionRound && round > normalizedInjectionRound
          ? `\n\nNote: The ${normalizedStrategyType} response was issued in round ${normalizedInjectionRound}. Agents are processing its ongoing effects.`
          : "");

      const roundPrompt = `You are simulating a crisis communication scenario. Simulate round ${round} of ${total_rounds}.

CRISIS CONTEXT:
${crisisContext}

AGENTS IN THIS SIMULATION:
${agentSummaries}

CURRENT NARRATIVE STATE (end of round ${round - 1}):
${previousNarrative}

CURRENT OVERALL SENTIMENT: ${previousSentiment.toFixed(2)} (scale: -1.0 very negative to +1.0 very positive)
${strategyContext}

For round ${round}, generate each agent's realistic reaction/response based on their persona and the current narrative.

Return a JSON object with:
- "agent_responses": array of {
    "agent_id": the agent's role (consumer/supporter/critic/media),
    "response": 2-3 sentence realistic response/reaction this agent would post or say,
    "sentiment_delta": float from -0.3 to +0.3 showing how this agent's reaction shifts overall sentiment,
    "amplification": float 0-1 showing how much this agent amplifies the crisis
  }
- "overall_sentiment": float -1.0 to 1.0 for end of this round
- "polarization_level": float 0.0 to 1.0 (how divided public opinion is)
- "negative_claim_spread": float 0.0 to 1.0 (how much negative claims are spreading)
- "stabilization_indicator": float 0.0 to 1.0 (how stable/settled the situation is)
- "narrative_state": 2-3 sentence summary of the overall narrative at end of this round

Ensure values are realistic and evolve logically from round to round.
Return ONLY valid JSON.`;

      let roundData;
      try {
        roundData = await chatJson({ prompt: roundPrompt, temperature: 0.75, maxRetries: 3 });
      } catch (error) {
        const errorMessage = getErrorMessage(error);
        const message = `Round ${round} failed: ${errorMessage}`;
        console.error(message, {
          ...Object.prototype.hasOwnProperty.call(error, "rawText") ? { rawText: (error as { rawText?: unknown }).rawText } : undefined,
          ...Object.prototype.hasOwnProperty.call(error, "status") ? { status: (error as { status?: number }).status } : undefined,
          round,
          case_id,
          run_id,
          promptLength: roundPrompt.length,
        });
        await supabase
          .from("simulation_runs")
          .update({
            status: "failed",
            error_message: message,
            completed_at: new Date().toISOString(),
            last_heartbeat_at: new Date().toISOString(),
          })
          .eq("id", run_id);
        return new Response(
          JSON.stringify({ error: message }),
          { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }

      if (!roundData || !Array.isArray(roundData.agent_responses) || typeof roundData.overall_sentiment !== "number") {
        const message = `Round ${round} failed: invalid model output structure`;
        console.error(message, formatRoundLog(round, case_id, run_id, run_type, strategy_type), {
          roundData,
          roundPromptLength: roundPrompt.length,
        });
        await supabase
          .from("simulation_runs")
          .update({
            status: "failed",
            error_message: message,
            completed_at: new Date().toISOString(),
            last_heartbeat_at: new Date().toISOString(),
          })
          .eq("id", run_id);
        return new Response(
          JSON.stringify({ error: message }),
          { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }

      const agentResponses = (roundData.agent_responses || []).map((r: {
        agent_id: string; response: string; sentiment_delta: number; amplification: number;
      }, idx: number) => ({
        agent_id: (agents || [])[idx]?.id || r.agent_id,
        role: r.agent_id,
        response: r.response,
        sentiment_delta: r.sentiment_delta,
        amplification: r.amplification,
      }));

      const { error: roundStateErr } = await supabase.from("round_states").insert({
        run_id,
        round_number: round,
        agent_responses: agentResponses,
        overall_sentiment: roundData.overall_sentiment ?? previousSentiment,
        polarization_level: roundData.polarization_level ?? 0.5,
        narrative_state: roundData.narrative_state ?? "",
        strategy_applied: strategyApplied,
      });
      if (roundStateErr) {
        const message = `Round ${round} failed: round_states write failed: ${roundStateErr.message}`;
        console.error(message, {
          ...formatRoundLog(round, case_id, run_id, run_type, strategy_type),
          error: roundStateErr,
          runId: run_id,
          round,
        });
        await supabase
          .from("simulation_runs")
          .update({
            status: "failed",
            error_message: message,
            completed_at: new Date().toISOString(),
            last_heartbeat_at: new Date().toISOString(),
          })
          .eq("id", run_id);
        return new Response(
          JSON.stringify({ error: message }),
          { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }

      const { error: metricsErr } = await supabase.from("metric_snapshots").insert({
        run_id,
        round_number: round,
        sentiment_score: roundData.overall_sentiment ?? previousSentiment,
        polarization_score: roundData.polarization_level ?? 0.5,
        negative_claim_spread: roundData.negative_claim_spread ?? 0.5,
        stabilization_indicator: roundData.stabilization_indicator ?? 0.3,
      });
      if (metricsErr) {
        const message = `Round ${round} failed: metric_snapshots write failed: ${metricsErr.message}`;
        console.error(message, {
          ...formatRoundLog(round, case_id, run_id, run_type, strategy_type),
          error: metricsErr,
          runId: run_id,
          round,
        });
        await supabase
          .from("simulation_runs")
          .update({
            status: "failed",
            error_message: message,
            completed_at: new Date().toISOString(),
            last_heartbeat_at: new Date().toISOString(),
          })
          .eq("id", run_id);
        return new Response(
          JSON.stringify({ error: message }),
          { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }

      previousSentiment = roundData.overall_sentiment ?? previousSentiment;
      previousNarrative = roundData.narrative_state ?? previousNarrative;
      await updateRunHeartbeat(supabase, run_id, { status: "running" });
    }

    await supabase
      .from("simulation_runs")
      .update({
        status: "completed",
        completed_at: new Date().toISOString(),
        last_heartbeat_at: new Date().toISOString(),
      })
      .eq("id", run_id);

    await supabase
      .from("crisis_cases")
      .update({ status: "simulated", updated_at: new Date().toISOString() })
      .eq("id", case_id);

    return new Response(
      JSON.stringify({ success: true, run_id }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (err) {
    const message = getErrorMessage(err);
    console.error(`Simulation failed: ${message}`);
    if (run_id) {
      const supabase = createClient(
        Deno.env.get("SUPABASE_URL")!,
        Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
      );
      await supabase
        .from("simulation_runs")
        .update({
          status: "failed",
          error_message: message,
          completed_at: new Date().toISOString(),
          last_heartbeat_at: new Date().toISOString(),
        })
        .eq("id", run_id);
    }
    return new Response(
      JSON.stringify({ error: message }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});

function getDefaultStrategyMessage(strategyType: string): string {
  const defaults: Record<string, string> = {
    apology: "We sincerely apologize for the harm caused. We take full responsibility and are committed to making things right.",
    clarification: "We want to clarify the facts: the situation has been misrepresented. Here is the accurate account of what occurred.",
    compensation: "We are offering full refunds and compensation to all affected customers. Please contact us directly to resolve this.",
    rebuttal: "The claims being circulated are inaccurate. We have conducted a thorough investigation and the evidence does not support these allegations.",
  };
  return defaults[strategyType] || "We are aware of the situation and are actively working to address all concerns.";
}
