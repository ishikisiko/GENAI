import { supabase } from "./supabase";
import {
  DEMO_CASE_ID,
  DEMO_CASE_TITLE,
  demoCase,
  demoGlobalDocs,
  demoDocs,
  demoEntities,
  demoRelations,
  demoClaims,
  demoAgents,
  demoRuns,
  demoRoundStates,
  demoMetrics,
} from "./demoData";

export async function isDemoAlreadySeeded(): Promise<boolean> {
  const { data } = await supabase
    .from("crisis_cases")
    .select("id")
    .eq("id", DEMO_CASE_ID)
    .maybeSingle();
  return data !== null;
}

export async function seedDemo(): Promise<string> {
  const alreadySeeded = await isDemoAlreadySeeded();
  if (alreadySeeded) return DEMO_CASE_ID;

  const { error: caseErr } = await supabase.from("crisis_cases").insert(demoCase);
  if (caseErr) throw new Error(`Failed to insert case: ${caseErr.message}`);

  const { error: globalDocsErr } = await supabase.from("global_source_documents").insert(demoGlobalDocs);
  if (globalDocsErr) throw new Error(`Failed to insert global documents: ${globalDocsErr.message}`);

  const { error: docsErr } = await supabase.from("source_documents").insert(demoDocs);
  if (docsErr) throw new Error(`Failed to insert documents: ${docsErr.message}`);

  const { error: entErr } = await supabase.from("entities").insert(demoEntities);
  if (entErr) throw new Error(`Failed to insert entities: ${entErr.message}`);

  const { error: claimErr } = await supabase.from("claims").insert(demoClaims);
  if (claimErr) throw new Error(`Failed to insert claims: ${claimErr.message}`);

  const { error: relErr } = await supabase.from("relations").insert(demoRelations);
  if (relErr) throw new Error(`Failed to insert relations: ${relErr.message}`);

  const { error: agentErr } = await supabase.from("agent_profiles").insert(demoAgents);
  if (agentErr) throw new Error(`Failed to insert agents: ${agentErr.message}`);

  const { error: runErr } = await supabase.from("simulation_runs").insert(demoRuns);
  if (runErr) throw new Error(`Failed to insert runs: ${runErr.message}`);

  const { error: roundErr } = await supabase.from("round_states").insert(demoRoundStates);
  if (roundErr) throw new Error(`Failed to insert rounds: ${roundErr.message}`);

  const { error: metErr } = await supabase.from("metric_snapshots").insert(demoMetrics);
  if (metErr) throw new Error(`Failed to insert metrics: ${metErr.message}`);

  return DEMO_CASE_ID;
}

export { DEMO_CASE_ID, DEMO_CASE_TITLE };
