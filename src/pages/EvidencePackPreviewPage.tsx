import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  PButton, PHeading, PIcon, PInlineNotification, PSpinner, PTag, PText,
} from "@porsche-design-system/components-react";
import PageHeader from "../components/PageHeader";
import { fetchEvidencePack, startEvidencePackGrounding } from "../lib/backend";
import { getErrorMessage } from "../lib/errors";
import { supabase } from "../lib/supabase";
import type { CrisisCase, EvidencePack, GraphExtractionSubmissionResponse } from "../lib/types";

export default function EvidencePackPreviewPage() {
  const { caseId, packId } = useParams<{ caseId: string; packId: string }>();
  const navigate = useNavigate();
  const [crisisCase, setCrisisCase] = useState<CrisisCase | null>(null);
  const [pack, setPack] = useState<EvidencePack | null>(null);
  const [groundingStatus, setGroundingStatus] = useState<GraphExtractionSubmissionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  const fetchPageData = useCallback(async () => {
    if (!caseId || !packId) return;
    const [{ data }, evidencePack] = await Promise.all([
      supabase.from("crisis_cases").select("*").eq("id", caseId).maybeSingle(),
      fetchEvidencePack(packId),
    ]);
    return { crisisCase: data, pack: evidencePack };
  }, [caseId, packId]);

  useEffect(() => {
    if (!caseId || !packId) return undefined;
    let cancelled = false;

    async function runInitialLoad() {
      try {
        const data = await fetchPageData();
        if (cancelled || !data) return;
        setCrisisCase(data.crisisCase);
        setPack(data.pack);
      } catch (error: unknown) {
        if (cancelled) return;
        setError(getErrorMessage(error, "Failed to load evidence pack."));
      }
      if (!cancelled) {
        setLoading(false);
      }
    }

    void runInitialLoad();

    return () => {
      cancelled = true;
    };
  }, [caseId, fetchPageData, packId]);

  async function startGrounding() {
    if (!packId) return;
    setStarting(true);
    setError("");
    try {
      const response = await startEvidencePackGrounding(packId);
      setGroundingStatus(response);
      setPack(await fetchEvidencePack(packId));
    } catch (error: unknown) {
      setError(getErrorMessage(error, "Failed to start grounding."));
    }
    setStarting(false);
  }

  if (loading) {
    return <div className="flex items-center justify-center min-h-full"><PSpinner size="medium" /></div>;
  }

  return (
    <div className="min-h-full">
      <PageHeader
        title="Evidence Pack"
        subtitle={crisisCase?.title}
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: crisisCase?.title || "Case", href: `/cases/${caseId}/documents` },
          { label: "Evidence Pack" },
        ]}
        action={pack && <PTag color={pack.status === "grounding_started" ? "notification-success-soft" : "background-frosted"}>{pack.status}</PTag>}
      />

      <div className="p-fluid-lg max-w-6xl">
        {error && (
          <PInlineNotification heading="Error" description={error} state="error" dismissButton className="mb-fluid-md" onDismiss={() => setError("")} />
        )}

        {!pack ? (
          <div className="bg-surface border border-contrast-low rounded-lg p-fluid-xl flex flex-col items-center gap-static-md text-center">
            <PIcon name="document" size="large" color="contrast-medium" />
            <PText className="text-contrast-medium">Evidence pack not found.</PText>
          </div>
        ) : (
          <div className="grid grid-cols-5 gap-fluid-md">
            <div className="col-span-3 flex flex-col gap-static-sm">
              {pack.sources.map((source) => (
                <div key={source.id} className="bg-surface border border-contrast-low rounded-lg p-fluid-sm">
                  <div className="flex items-start justify-between gap-static-md">
                    <div className="min-w-0">
                      <div className="flex items-center gap-static-xs flex-wrap mb-static-xs">
                        <PTag color="notification-info-soft">{source.source_type}</PTag>
                        <PTag color="background-frosted">{Math.round(source.total_score * 100)} score</PTag>
                        {source.source_document_id && <PTag color="notification-success-soft">Document</PTag>}
                      </div>
                      <PHeading size="small">{source.title}</PHeading>
                      {source.url && <PText size="small" className="text-contrast-low truncate mt-static-xs">{source.url}</PText>}
                    </div>
                  </div>

                  <PText size="small" className="text-contrast-medium mt-static-sm line-clamp-4">
                    {source.excerpt || source.content}
                  </PText>

                  <div className="grid grid-cols-6 gap-static-xs mt-static-sm">
                    {Object.entries(source.score_dimensions).map(([key, value]) => (
                      <div key={key} className="bg-canvas rounded p-static-xs">
                        <PText size="x-small" className="text-contrast-medium">{key.replace("_", " ")}</PText>
                        <PText size="small" weight="semi-bold">{Math.round(value * 100)}</PText>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="col-span-2">
              <div className="bg-surface border border-contrast-low rounded-lg p-fluid-md sticky top-fluid-md flex flex-col gap-fluid-sm">
                <PHeading size="small">{pack.title}</PHeading>
                <div className="grid grid-cols-2 gap-static-xs">
                  <div className="bg-canvas rounded p-static-sm text-center">
                    <PText size="small" weight="semi-bold">{pack.source_count}</PText>
                    <PText size="x-small" className="text-contrast-medium">Sources</PText>
                  </div>
                  <div className="bg-canvas rounded p-static-sm text-center">
                    <PText size="small" weight="semi-bold">{pack.sources.filter((source) => source.source_document_id).length}</PText>
                    <PText size="x-small" className="text-contrast-medium">Documents</PText>
                  </div>
                </div>

                <PText size="small" className="text-contrast-medium">
                  Grounding converts this reviewed pack into case documents and queues the existing GraphRAG extraction job.
                </PText>

                <PButton
                  icon="arrow-right"
                  loading={starting}
                  disabled={starting || pack.sources.length === 0}
                  onClick={startGrounding}
                >
                  Start Grounding
                </PButton>

                {groundingStatus && (
                  <div className="bg-canvas rounded p-static-sm">
                    <PText size="small" weight="semi-bold">Grounding queued</PText>
                    <PText size="small" className="text-contrast-medium mt-static-xs">
                      {groundingStatus.document_count} documents sent to GraphRAG.
                    </PText>
                    <PButton
                      variant="secondary"
                      className="mt-static-sm"
                      onClick={() => navigate(`/cases/${caseId}/grounding`)}
                    >
                      Open Grounding
                    </PButton>
                  </div>
                )}

                <PButton variant="secondary" onClick={() => navigate(`/cases/${caseId}/documents`)}>
                  Back to Documents
                </PButton>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
