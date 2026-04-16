import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";
import { chatJson, getLlmConfig } from "../_shared/llm.ts";

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

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 200, headers: corsHeaders });
  }

  try {
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const body: RunSimulationRequest = await req.json();
    const { case_id, run_type, total_rounds = 5, strategy_type, strategy_message, injection_round } = body;

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

    const [{ data: agents }, { data: claims }, { data: entities }, { data: caseData }] = await Promise.all([
      supabase.from("agent_profiles").select("*").eq("case_id", case_id),
      supabase.from("claims").select("*").eq("case_id", case_id),
      supabase.from("entities").select("*").eq("case_id", case_id),
      supabase.from("crisis_cases").select("*").eq("id", case_id).maybeSingle(),
    ]);

    const { data: run } = await supabase
      .from("simulation_runs")
      .insert({
        case_id,
        run_type,
        strategy_type: strategy_type || null,
        strategy_message: strategy_message || null,
        injection_round: injection_round || null,
        total_rounds,
        status: "running",
      })
      .select()
      .maybeSingle();

    if (!run) {
      return new Response(
        JSON.stringify({ error: "Failed to create simulation run" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const run_id = run.id;

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
      const isInjectionRound = run_type === "intervention" && injection_round && round === injection_round;
      const strategyApplied = isInjectionRound ? strategy_type : null;

      const strategyContext = isInjectionRound
        ? `\n\nCRISIS RESPONSE STRATEGY INJECTED (Round ${round}):
Strategy Type: ${strategy_type?.toUpperCase()}
Message: "${strategy_message || getDefaultStrategyMessage(strategy_type || "")}"
This response has just been made public. All agents are now aware of this official response.`
        : (run_type === "intervention" && injection_round && round > injection_round
          ? `\n\nNote: The ${strategy_type} response was issued in round ${injection_round}. Agents are processing its ongoing effects.`
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
        roundData = await chatJson({ prompt: roundPrompt, temperature: 0.75 });
      } catch {
        await supabase.from("simulation_runs").update({ status: "failed", error_message: "OpenAI API error" }).eq("id", run_id);
        return new Response(
          JSON.stringify({ error: "LLM API error during simulation" }),
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

      await supabase.from("round_states").insert({
        run_id,
        round_number: round,
        agent_responses: agentResponses,
        overall_sentiment: roundData.overall_sentiment ?? previousSentiment,
        polarization_level: roundData.polarization_level ?? 0.5,
        narrative_state: roundData.narrative_state ?? "",
        strategy_applied: strategyApplied,
      });

      await supabase.from("metric_snapshots").insert({
        run_id,
        round_number: round,
        sentiment_score: roundData.overall_sentiment ?? previousSentiment,
        polarization_score: roundData.polarization_level ?? 0.5,
        negative_claim_spread: roundData.negative_claim_spread ?? 0.5,
        stabilization_indicator: roundData.stabilization_indicator ?? 0.3,
      });

      previousSentiment = roundData.overall_sentiment ?? previousSentiment;
      previousNarrative = roundData.narrative_state ?? previousNarrative;
    }

    await supabase
      .from("simulation_runs")
      .update({ status: "completed", completed_at: new Date().toISOString() })
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
    return new Response(
      JSON.stringify({ error: String(err) }),
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
