import type { ComponentProps } from "react";
import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  PButton, PText, PHeading, PSpinner, PInlineNotification,
  PTag, PDivider, PIcon, PButtonPure,
} from "@porsche-design-system/components-react";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import { getErrorMessage } from "../lib/errors";
import { supabase, EDGE_FN_BASE, edgeHeaders } from "../lib/supabase";
import type { CrisisCase, Entity, Relation, Claim } from "../lib/types";

type IconName = NonNullable<ComponentProps<typeof PIcon>["name"]>;
type TagColor = NonNullable<ComponentProps<typeof PTag>["color"]>;

const ENTITY_TYPE_COLORS: Record<string, TagColor> = {
  person: "notification-info-soft",
  organization: "notification-warning-soft",
  product: "notification-success-soft",
  event: "background-frosted",
  location: "notification-error-soft",
};

const CREDIBILITY_COLORS: Record<string, TagColor> = {
  high: "notification-success-soft",
  medium: "notification-warning-soft",
  low: "notification-error-soft",
};

const CLAIM_TYPE_COLORS: Record<string, TagColor> = {
  fact: "notification-success-soft",
  allegation: "notification-error-soft",
  statement: "notification-info-soft",
  event: "background-frosted",
};

export default function GroundingPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();

  const [crisisCase, setCrisisCase] = useState<CrisisCase | null>(null);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [relations, setRelations] = useState<Relation[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"entities" | "relations" | "claims">("entities");

  const load = useCallback(async () => {
    setLoading(true);
    const [{ data: c }, { data: ents }, { data: rels }, { data: cls }] = await Promise.all([
      supabase.from("crisis_cases").select("*").eq("id", caseId!).maybeSingle(),
      supabase.from("entities").select("*").eq("case_id", caseId!).order("entity_type"),
      supabase.from("relations").select("*").eq("case_id", caseId!),
      supabase.from("claims").select("*").eq("case_id", caseId!).order("credibility"),
    ]);
    setCrisisCase(c);
    setEntities(ents ?? []);
    setRelations(rels ?? []);
    setClaims(cls ?? []);
    setLoading(false);
  }, [caseId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (caseId) void load();
  }, [caseId, load]);

  async function generateAgents() {
    setGenerating(true);
    setError("");
    try {
      const resp = await fetch(`${EDGE_FN_BASE}/generate-agents`, {
        method: "POST",
        headers: edgeHeaders,
        body: JSON.stringify({ case_id: caseId }),
      });
      const result = await resp.json();
      if (!resp.ok || result.error) {
        setError(result.error || "Agent generation failed.");
        setGenerating(false);
        return;
      }
      navigate(`/cases/${caseId}/simulation`);
    } catch (error: unknown) {
      setError(getErrorMessage(error, "Agent generation failed."));
    }
    setGenerating(false);
  }

  const entityById = (id: string | null) => entities.find((e) => e.id === id);

  const tabs = [
    { key: "entities" as const, label: "Entities", count: entities.length, icon: "group" },
    { key: "relations" as const, label: "Relations", count: relations.length, icon: "linked" },
    { key: "claims" as const, label: "Claims", count: claims.length, icon: "document" },
  ] satisfies { key: "entities" | "relations" | "claims"; label: string; count: number; icon: IconName }[];

  const summaryStats = [
    { label: "Entities", value: entities.length, icon: "group" },
    { label: "Relations", value: relations.length, icon: "linked" },
    { label: "Claims", value: claims.length, icon: "document" },
  ] satisfies { label: string; value: number; icon: IconName }[];

  if (loading) return (
    <div className="flex items-center justify-center min-h-full"><PSpinner size="medium" /></div>
  );

  const isEmpty = entities.length === 0 && claims.length === 0;

  return (
    <div className="min-h-full">
      <PageHeader
        title="GraphRAG Grounding"
        subtitle={crisisCase?.title}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: crisisCase?.title || "Case" }, { label: "Grounding" }]}
        action={crisisCase && <StatusBadge status={crisisCase.status} />}
      />

      <div className="p-fluid-lg max-w-5xl">
        {error && (
          <PInlineNotification heading="Error" description={error} state="error" dismissButton className="mb-fluid-md" onDismiss={() => setError("")} />
        )}

        {isEmpty ? (
          <div className="bg-surface border border-contrast-low rounded-lg p-fluid-xl flex flex-col items-center gap-static-md text-center">
            <PIcon name="brain" size="large" color="contrast-medium" />
            <PText className="text-contrast-medium">No grounding data yet. Go back and extract the knowledge graph first.</PText>
            <PButton variant="secondary" icon="arrow-left" onClick={() => navigate(`/cases/${caseId}/documents`)}>
              Back to Documents
            </PButton>
          </div>
        ) : (
          <div className="grid grid-cols-4 gap-fluid-md">
            <div className="col-span-3 flex flex-col gap-fluid-md">
              <div className="flex gap-static-sm">
                {tabs.map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={`flex items-center gap-static-xs px-static-md py-static-sm rounded border transition-colors ${
                      activeTab === tab.key
                        ? "border-primary bg-primary text-[white]"
                        : "border-contrast-low bg-surface text-contrast-medium hover:border-primary hover:text-primary"
                    }`}
                    style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif" }}
                  >
                    <PIcon name={tab.icon as IconName} size="small" color="inherit" />
                    <span className="text-sm font-medium" style={{ color: "inherit" }}>{tab.label}</span>
                    <span className={`text-xs rounded-full px-1.5 ${activeTab === tab.key ? "bg-[rgba(255,255,255,0.3)] text-[white]" : "bg-canvas text-contrast-medium"}`}>
                      {tab.count}
                    </span>
                  </button>
                ))}
              </div>

              <div className="flex flex-col gap-static-sm">
                {activeTab === "entities" && entities.map((e) => (
                  <div key={e.id} className="bg-surface border border-contrast-low rounded-lg p-fluid-sm flex gap-static-md items-start">
                    <PTag color={ENTITY_TYPE_COLORS[e.entity_type]}>{e.entity_type}</PTag>
                    <div className="flex-1">
                      <PText size="small" weight="semi-bold">{e.name}</PText>
                      <PText size="small" className="text-contrast-medium mt-static-xs">{e.description}</PText>
                    </div>
                  </div>
                ))}

                {activeTab === "relations" && (
                  relations.length === 0 ? (
                    <PText className="text-contrast-medium p-fluid-md">No relations extracted.</PText>
                  ) : relations.map((r) => {
                    const src = entityById(r.source_entity_id);
                    const tgt = entityById(r.target_entity_id);
                    return (
                      <div key={r.id} className="bg-surface border border-contrast-low rounded-lg p-fluid-sm">
                        <div className="flex items-center gap-static-sm flex-wrap">
                          <PTag color="notification-info-soft">{src?.name || "?"}</PTag>
                          <PIcon name="arrow-right" size="small" color="contrast-medium" />
                          <PText size="small" className="text-primary font-medium bg-canvas border border-contrast-low rounded px-static-sm py-[2px]">
                            {r.relation_type}
                          </PText>
                          <PIcon name="arrow-right" size="small" color="contrast-medium" />
                          <PTag color="notification-warning-soft">{tgt?.name || "?"}</PTag>
                        </div>
                        <PText size="small" className="text-contrast-medium mt-static-sm">{r.description}</PText>
                      </div>
                    );
                  })
                )}

                {activeTab === "claims" && claims.map((c) => (
                  <div key={c.id} className="bg-surface border border-contrast-low rounded-lg p-fluid-sm flex gap-static-md items-start">
                    <div className="flex flex-col gap-static-xs shrink-0">
                      <PTag color={CLAIM_TYPE_COLORS[c.claim_type]}>{c.claim_type}</PTag>
                      <PTag color={CREDIBILITY_COLORS[c.credibility]}>{c.credibility}</PTag>
                    </div>
                    <PText size="small" className="text-primary">{c.content}</PText>
                  </div>
                ))}
              </div>
            </div>

            <div className="col-span-1">
              <div className="bg-surface border border-contrast-low rounded-lg p-fluid-md sticky top-fluid-md flex flex-col gap-fluid-sm">
                <PHeading size="small">Graph Summary</PHeading>
                <div className="flex flex-col gap-static-sm">
                  {summaryStats.map((s) => (
                    <div key={s.label} className="flex items-center justify-between bg-canvas rounded p-static-sm">
                      <div className="flex items-center gap-static-xs">
                        <PIcon name={s.icon} size="small" color="contrast-medium" />
                        <PText size="small" className="text-contrast-medium">{s.label}</PText>
                      </div>
                      <PText size="small" weight="semi-bold">{s.value}</PText>
                    </div>
                  ))}
                </div>

                <PDivider />

                <PText size="small" className="text-contrast-medium">
                  Review the extracted knowledge graph above. The agents generated in the next step will be grounded in these entities and claims.
                </PText>

                <PButton
                  loading={generating}
                  disabled={generating || isEmpty}
                  icon="arrow-right"
                  onClick={generateAgents}
                >
                  {generating ? "Generating..." : "Generate Agents"}
                </PButton>

                <PButtonPure
                  icon="arrow-left"
                  onClick={() => navigate(`/cases/${caseId}/documents`)}
                >
                  Back to Documents
                </PButtonPure>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
