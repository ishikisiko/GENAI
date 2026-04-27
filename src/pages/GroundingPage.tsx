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
import { generateAgents as requestAgentGeneration, BackendApiError } from "../lib/backend";
import { supabase } from "../lib/supabase";
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
  const [acceptedCandidateCount, setAcceptedCandidateCount] = useState(0);
  const [latestAcceptedDiscoveryJobId, setLatestAcceptedDiscoveryJobId] = useState<string | null>(null);
  const [evidencePackCount, setEvidencePackCount] = useState(0);
  const [latestEvidencePackId, setLatestEvidencePackId] = useState<string | null>(null);
  const [sourceDocumentCount, setSourceDocumentCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"entities" | "relations" | "claims">("entities");

  const fetchGroundingData = useCallback(async () => {
    const [
      { data: c },
      { data: ents },
      { data: rels },
      { data: cls },
      { data: accepted, count: acceptedCount },
      { data: packs, count: packCount },
      { count: documentCount },
    ] = await Promise.all([
      supabase.from("crisis_cases").select("*").eq("id", caseId!).maybeSingle(),
      supabase.from("entities").select("*").eq("case_id", caseId!).order("entity_type"),
      supabase.from("relations").select("*").eq("case_id", caseId!),
      supabase.from("claims").select("*").eq("case_id", caseId!).order("credibility"),
      supabase
        .from("source_candidates")
        .select("discovery_job_id", { count: "exact" })
        .eq("case_id", caseId!)
        .eq("review_status", "accepted")
        .order("updated_at", { ascending: false })
        .limit(1),
      supabase
        .from("evidence_packs")
        .select("id", { count: "exact" })
        .eq("case_id", caseId!)
        .order("created_at", { ascending: false })
        .limit(1),
      supabase
        .from("source_documents")
        .select("id", { count: "exact", head: true })
        .eq("case_id", caseId!),
    ]);
    return {
      crisisCase: c,
      entities: ents ?? [],
      relations: rels ?? [],
      claims: cls ?? [],
      acceptedCandidateCount: acceptedCount ?? 0,
      latestAcceptedDiscoveryJobId: accepted?.[0]?.discovery_job_id ?? null,
      evidencePackCount: packCount ?? 0,
      latestEvidencePackId: packs?.[0]?.id ?? null,
      sourceDocumentCount: documentCount ?? 0,
    };
  }, [caseId]);

  useEffect(() => {
    if (!caseId) return undefined;
    let cancelled = false;

    async function runInitialLoad() {
      const data = await fetchGroundingData();
      if (cancelled) return;
      setCrisisCase(data.crisisCase);
      setEntities(data.entities);
      setRelations(data.relations);
      setClaims(data.claims);
      setAcceptedCandidateCount(data.acceptedCandidateCount);
      setLatestAcceptedDiscoveryJobId(data.latestAcceptedDiscoveryJobId);
      setEvidencePackCount(data.evidencePackCount);
      setLatestEvidencePackId(data.latestEvidencePackId);
      setSourceDocumentCount(data.sourceDocumentCount);
      setLoading(false);
    }

    void runInitialLoad();

    return () => {
      cancelled = true;
    };
  }, [caseId, fetchGroundingData]);

  async function handleGenerateAgents() {
    setGenerating(true);
    setError("");
    try {
      await requestAgentGeneration(caseId!);
      navigate(`/cases/${caseId}/simulation`);
    } catch (error: unknown) {
      if (error instanceof BackendApiError) {
        setError(error.message || "Agent generation failed.");
      } else {
        setError(getErrorMessage(error, "Agent generation failed."));
      }
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
  const emptyState = (() => {
    if (acceptedCandidateCount > 0 && evidencePackCount === 0) {
      return {
        message: `${acceptedCandidateCount} accepted source${acceptedCandidateCount > 1 ? "s" : ""} waiting for an Evidence Pack.`,
        detail: "Accepted sources are still review decisions. Create an Evidence Pack before they become grounding material.",
        button: "Open Candidate Review",
        onClick: () => navigate(
          latestAcceptedDiscoveryJobId
            ? `/cases/${caseId}/source-discovery/${latestAcceptedDiscoveryJobId}/review`
            : `/cases/${caseId}/source-discovery`
        ),
      };
    }
    if (evidencePackCount > 0 && sourceDocumentCount === 0) {
      return {
        message: "Evidence Pack created, but it has not been grounded into Documents yet.",
        detail: "Open the Evidence Pack and start grounding to convert reviewed sources into case documents.",
        button: "Open Evidence Pack",
        onClick: () => navigate(
          latestEvidencePackId
            ? `/cases/${caseId}/evidence-packs/${latestEvidencePackId}`
            : `/cases/${caseId}/documents`
        ),
      };
    }
    if (sourceDocumentCount > 0) {
      return {
        message: `${sourceDocumentCount} document${sourceDocumentCount > 1 ? "s" : ""} ready for graph extraction.`,
        detail: "Extract the knowledge graph from Documents before reviewing grounding results here.",
        button: "Open Documents",
        onClick: () => navigate(`/cases/${caseId}/documents`),
      };
    }
    return {
      message: "No grounding data yet.",
      detail: "Add source documents or discover sources before extracting the knowledge graph.",
      button: "Open Documents",
      onClick: () => navigate(`/cases/${caseId}/documents`),
    };
  })();

  return (
    <div className="min-h-full">
      <PageHeader
        title="GraphRAG Grounding"
        subtitle={crisisCase?.title}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: crisisCase?.title || "Case" }, { label: "Grounding" }]}
        action={crisisCase && <StatusBadge status={crisisCase.status} />}
      />

      <div className="p-fluid-lg w-full">
        {error && (
          <PInlineNotification heading="Error" description={error} state="error" dismissButton className="mb-fluid-md" onDismiss={() => setError("")} />
        )}

        {isEmpty ? (
          <div className="bg-surface border border-contrast-low rounded-lg p-fluid-xl flex flex-col items-center gap-static-md text-center">
            <PIcon name="brain" size="large" color="contrast-medium" />
            <PText className="text-contrast-medium">{emptyState.message}</PText>
            <PText size="small" className="text-contrast-medium max-w-xl">{emptyState.detail}</PText>
            <PButton variant="secondary" icon="arrow-left" onClick={emptyState.onClick}>
              {emptyState.button}
            </PButton>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-fluid-md xl:grid-cols-4">
            <div className="flex flex-col gap-fluid-md xl:col-span-3">
              <div className="flex flex-wrap gap-static-sm">
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
                  <div key={e.id} className="bg-surface border border-contrast-low rounded-lg p-fluid-sm flex flex-col gap-static-sm sm:flex-row sm:items-start sm:gap-static-md">
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
                  <div key={c.id} className="bg-surface border border-contrast-low rounded-lg p-fluid-sm flex flex-col gap-static-sm sm:flex-row sm:items-start sm:gap-static-md">
                    <div className="flex flex-wrap gap-static-xs shrink-0 sm:flex-col">
                      <PTag color={CLAIM_TYPE_COLORS[c.claim_type]}>{c.claim_type}</PTag>
                      <PTag color={CREDIBILITY_COLORS[c.credibility]}>{c.credibility}</PTag>
                    </div>
                    <PText size="small" className="text-primary">{c.content}</PText>
                  </div>
                ))}
              </div>
            </div>

            <div className="xl:col-span-1">
              <div className="bg-surface border border-contrast-low rounded-lg p-fluid-md flex flex-col gap-fluid-sm xl:sticky xl:top-fluid-md">
                <PHeading size="small">Graph Summary</PHeading>
                <div className="grid grid-cols-1 gap-static-sm sm:grid-cols-3 xl:grid-cols-1">
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
                  onClick={handleGenerateAgents}
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
