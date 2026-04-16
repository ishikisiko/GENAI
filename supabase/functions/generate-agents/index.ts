import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";
import { chatJson, getLlmConfig } from "../_shared/llm.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey",
};

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 200, headers: corsHeaders });
  }

  try {
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const { case_id } = await req.json();

    if (!case_id) {
      return new Response(
        JSON.stringify({ error: "case_id is required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const [{ data: entities }, { data: claims }, { data: caseData }] = await Promise.all([
      supabase.from("entities").select("*").eq("case_id", case_id),
      supabase.from("claims").select("*").eq("case_id", case_id),
      supabase.from("crisis_cases").select("*").eq("id", case_id).maybeSingle(),
    ]);

    const { apiKey } = getLlmConfig();
    if (!apiKey) {
      return new Response(
        JSON.stringify({ error: "LLM_API_KEY or OPENAI_API_KEY not configured" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const graphSummary = `
Crisis: ${caseData?.title}
${caseData?.description}

Key Entities: ${(entities || []).map((e: { name: string; entity_type: string }) => `${e.name} (${e.entity_type})`).join(", ")}

Key Claims:
${(claims || []).slice(0, 10).map((c: { claim_type: string; content: string }) => `- [${c.claim_type}] ${c.content}`).join("\n")}
`;

    const prompt = `You are a crisis communication expert. Based on the crisis scenario below, generate 4 stakeholder agent profiles that will participate in a public opinion simulation.

CRISIS CONTEXT:
${graphSummary}

Generate exactly 4 agents with these roles (one each):
1. consumer - An affected consumer/customer
2. supporter - A brand/organization supporter or loyal customer
3. critic - A vocal critic, activist, or skeptical journalist
4. media - A media outlet or journalist reporting on the crisis

For each agent return:
- role: (one of: consumer, supporter, critic, media)
- stance: brief stance description (e.g. "Deeply concerned and disappointed", "Cautiously defending the brand")
- concern: their primary concern in this crisis (1-2 sentences)
- emotional_sensitivity: integer 1-10 (how emotionally reactive they are)
- spread_tendency: integer 1-10 (how likely they are to spread information)
- persona_description: 2-3 sentence vivid description of who this person is
- initial_beliefs: array of 3-5 belief strings grounded in the crisis facts

Return ONLY a valid JSON object with key "agents" containing the array.`;

    const extracted = await chatJson({ prompt, temperature: 0.7 });

    await supabase.from("agent_profiles").delete().eq("case_id", case_id);

    const agentsData = (extracted.agents || []).map((a: {
      role: string; stance: string; concern: string;
      emotional_sensitivity: number; spread_tendency: number;
      persona_description: string; initial_beliefs: string[];
    }) => ({
      case_id,
      role: a.role,
      stance: a.stance,
      concern: a.concern,
      emotional_sensitivity: Math.min(10, Math.max(1, a.emotional_sensitivity)),
      spread_tendency: Math.min(10, Math.max(1, a.spread_tendency)),
      persona_description: a.persona_description,
      initial_beliefs: a.initial_beliefs || [],
    }));

    const { data: insertedAgents } = await supabase
      .from("agent_profiles")
      .insert(agentsData)
      .select();

    await supabase
      .from("crisis_cases")
      .update({ status: "agents_ready", updated_at: new Date().toISOString() })
      .eq("id", case_id);

    return new Response(
      JSON.stringify({ success: true, agents: insertedAgents }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (err) {
    return new Response(
      JSON.stringify({ error: String(err) }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
