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

interface ExtractedEntity {
  name: string;
  entity_type: string;
  description: string;
}

interface ExtractedRelation {
  source_entity_name: string;
  target_entity_name: string;
  relation_type: string;
  description: string;
}

interface ExtractedClaim {
  content: string;
  claim_type: string;
  credibility: string;
}

interface PartialGraph {
  source_doc_id: string;
  entities: ExtractedEntity[];
  relations: ExtractedRelation[];
  claims: ExtractedClaim[];
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

    const { apiKey } = getLlmConfig();
    if (!apiKey) {
      return new Response(
        JSON.stringify({ error: "LLM_API_KEY or OPENAI_API_KEY not configured in function secrets" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const partialGraphs = (await Promise.all(
      documents.map((document) => extractDocumentGraph(document))
    )).filter((partial): partial is PartialGraph => partial !== null);

    if (partialGraphs.length === 0) {
      return new Response(
        JSON.stringify({ error: "All document extraction attempts failed." }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const merged = mergePartialGraphs(partialGraphs);

    await supabase.from("entities").delete().eq("case_id", case_id);
    await supabase.from("claims").delete().eq("case_id", case_id);

    const entitiesData = merged.entities.map((entity) => ({
      case_id,
      name: entity.name,
      entity_type: entity.entity_type,
      description: entity.description,
    }));

    const { data: insertedEntities } = entitiesData.length > 0
      ? await supabase.from("entities").insert(entitiesData).select()
      : { data: [] };

    const entityMap: Record<string, string> = {};
    (insertedEntities || []).forEach((e: { id: string; name: string }) => {
      entityMap[normalizeName(e.name)] = e.id;
    });

    await supabase.from("relations").delete().eq("case_id", case_id);

    const relationsData = merged.relations
      .filter((relation) =>
        entityMap[normalizeName(relation.source_entity_name)] && entityMap[normalizeName(relation.target_entity_name)]
      )
      .map((relation) => ({
        case_id,
        source_entity_id: entityMap[normalizeName(relation.source_entity_name)],
        target_entity_id: entityMap[normalizeName(relation.target_entity_name)],
        relation_type: relation.relation_type,
        description: relation.description,
      }));

    if (relationsData.length > 0) {
      await supabase.from("relations").insert(relationsData);
    }

    const claimsData = merged.claims.map((claim) => ({
      case_id,
      content: claim.content,
      claim_type: claim.claim_type,
      credibility: claim.credibility,
      source_doc_id: claim.source_doc_id,
    }));

    if (claimsData.length > 0) {
      await supabase.from("claims").insert(claimsData);
    }

    await supabase
      .from("crisis_cases")
      .update({ status: "grounded", updated_at: new Date().toISOString() })
      .eq("id", case_id);

    return new Response(
      JSON.stringify({
        success: true,
        processed_documents: partialGraphs.length,
        failed_documents: documents.length - partialGraphs.length,
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

async function extractDocumentGraph(document: ExtractGraphRequest["documents"][number]): Promise<PartialGraph | null> {
  const prompt = `You are a knowledge graph extraction expert. Analyze the following single crisis-related document and extract structured information.

DOCUMENT:
[${document.doc_type.toUpperCase()}] ${document.title}
${document.content}

Extract and return a JSON object with:
1. "entities": array of {name, entity_type (person/organization/product/event/location), description}
2. "relations": array of {source_entity_name, target_entity_name, relation_type, description}
3. "claims": array of {content, claim_type (allegation/fact/statement/event), credibility (high/medium/low)}

Rules:
- Extract 2-8 entities, up to 5 relations, and 2-8 claims from this document only
- Focus on crisis-relevant entities, events, allegations, and official statements
- Do not invent facts that are not grounded in this document
- Use concise but specific descriptions

Return ONLY valid JSON, no markdown or explanation.`;

  try {
    const extracted = await chatJson({ prompt, temperature: 0.2, maxRetries: 3 });
    return {
      source_doc_id: document.id,
      entities: Array.isArray(extracted.entities) ? extracted.entities : [],
      relations: Array.isArray(extracted.relations) ? extracted.relations : [],
      claims: Array.isArray(extracted.claims) ? extracted.claims : [],
    };
  } catch (error) {
    console.error("Failed to extract graph from document", {
      doc_id: document.id,
      title: document.title,
      doc_type: document.doc_type,
      error: error instanceof Error ? error.message : String(error),
    });
    return null;
  }
}

function normalizeName(value: string): string {
  return value.trim().replace(/\s+/g, " ").toLowerCase();
}

function normalizeText(value: string): string {
  return value.trim().replace(/\s+/g, " ").toLowerCase();
}

function mergePartialGraphs(partials: PartialGraph[]) {
  const entityMap = new Map<string, ExtractedEntity>();
  const relationMap = new Map<string, ExtractedRelation>();
  const claimMap = new Map<string, ExtractedClaim & { source_doc_id: string | null }>();

  for (const partial of partials) {
    for (const entity of partial.entities) {
      if (!entity?.name) continue;
      const key = normalizeName(entity.name);
      if (!entityMap.has(key)) {
        entityMap.set(key, {
          name: entity.name.trim(),
          entity_type: entity.entity_type || "organization",
          description: entity.description?.trim() || "",
        });
      }
    }

    for (const relation of partial.relations) {
      if (!relation?.source_entity_name || !relation?.target_entity_name || !relation?.relation_type) continue;
      const key = [
        normalizeName(relation.source_entity_name),
        relation.relation_type.trim().toLowerCase(),
        normalizeName(relation.target_entity_name),
      ].join("|");

      if (!relationMap.has(key)) {
        relationMap.set(key, {
          source_entity_name: relation.source_entity_name.trim(),
          target_entity_name: relation.target_entity_name.trim(),
          relation_type: relation.relation_type.trim(),
          description: relation.description?.trim() || "",
        });
      }
    }

    for (const claim of partial.claims) {
      if (!claim?.content) continue;
      const key = `${claim.claim_type?.trim().toLowerCase() || "fact"}|${normalizeText(claim.content)}`;
      if (!claimMap.has(key)) {
        claimMap.set(key, {
          content: claim.content.trim(),
          claim_type: claim.claim_type || "fact",
          credibility: claim.credibility || "medium",
          source_doc_id: partial.source_doc_id,
        });
      }
    }
  }

  return {
    entities: Array.from(entityMap.values()),
    relations: Array.from(relationMap.values()),
    claims: Array.from(claimMap.values()),
  };
}
