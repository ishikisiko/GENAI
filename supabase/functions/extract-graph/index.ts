import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";
import { chatJson, getLlmConfig } from "../_shared/llm.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey",
};

interface ExtractGraphRequest {
  case_id: string;
  documents: Array<{ id: string; content: string; doc_type: string; title: string }>;
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

    const { case_id, documents }: ExtractGraphRequest = await req.json();

    if (!case_id || !documents || documents.length === 0) {
      return new Response(
        JSON.stringify({ error: "case_id and documents are required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const combinedText = documents
      .map((d) => `[${d.doc_type.toUpperCase()}] ${d.title}\n${d.content}`)
      .join("\n\n---\n\n");

    const { apiKey } = getLlmConfig();
    if (!apiKey) {
      return new Response(
        JSON.stringify({ error: "LLM_API_KEY or OPENAI_API_KEY not configured in function secrets" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const prompt = `You are a knowledge graph extraction expert. Analyze the following crisis-related documents and extract structured information.

DOCUMENTS:
${combinedText}

Extract and return a JSON object with:
1. "entities": array of {name, entity_type (person/organization/product/event/location), description}
2. "relations": array of {source_entity_name, target_entity_name, relation_type, description}
3. "claims": array of {content, claim_type (allegation/fact/statement/event), credibility (high/medium/low)}

Rules:
- Extract 5-15 entities, 4-10 relations, 6-15 claims
- Focus on crisis-relevant entities (involved parties, products, events)
- Claims should capture key allegations, facts, statements about the crisis
- Relations should describe how entities connect in the context of the crisis
- Be specific and factual, grounded in the text

Return ONLY valid JSON, no markdown or explanation.`;

    const extracted = await chatJson({ prompt, temperature: 0.3 });

    await supabase.from("entities").delete().eq("case_id", case_id);
    await supabase.from("claims").delete().eq("case_id", case_id);

    const entitiesData = (extracted.entities || []).map((e: { name: string; entity_type: string; description: string }) => ({
      case_id,
      name: e.name,
      entity_type: e.entity_type,
      description: e.description,
    }));

    const { data: insertedEntities } = await supabase
      .from("entities")
      .insert(entitiesData)
      .select();

    const entityMap: Record<string, string> = {};
    (insertedEntities || []).forEach((e: { id: string; name: string }) => {
      entityMap[e.name] = e.id;
    });

    await supabase.from("relations").delete().eq("case_id", case_id);

    const relationsData = (extracted.relations || [])
      .filter((r: { source_entity_name: string; target_entity_name: string }) =>
        entityMap[r.source_entity_name] && entityMap[r.target_entity_name]
      )
      .map((r: { source_entity_name: string; target_entity_name: string; relation_type: string; description: string }) => ({
        case_id,
        source_entity_id: entityMap[r.source_entity_name],
        target_entity_id: entityMap[r.target_entity_name],
        relation_type: r.relation_type,
        description: r.description,
      }));

    await supabase.from("relations").insert(relationsData);

    const claimsData = (extracted.claims || []).map((c: { content: string; claim_type: string; credibility: string }, i: number) => ({
      case_id,
      content: c.content,
      claim_type: c.claim_type,
      credibility: c.credibility,
      source_doc_id: documents[i % documents.length]?.id || null,
    }));

    await supabase.from("claims").insert(claimsData);

    await supabase
      .from("crisis_cases")
      .update({ status: "grounded", updated_at: new Date().toISOString() })
      .eq("id", case_id);

    return new Response(
      JSON.stringify({
        success: true,
        entities_count: entitiesData.length,
        relations_count: relationsData.length,
        claims_count: claimsData.length,
      }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (err) {
    return new Response(
      JSON.stringify({ error: String(err) }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
