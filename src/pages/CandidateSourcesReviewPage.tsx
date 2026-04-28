import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  PButton, PHeading, PIcon, PInlineNotification, PSpinner, PTag, PText,
} from "@porsche-design-system/components-react";
import PageHeader from "../components/PageHeader";
import {
  createEvidencePack,
  fetchSourceTopics,
  fetchSourceCandidates,
  fetchSourceDiscoveryJob,
  saveSourceCandidateToLibrary,
  updateSourceCandidateReview,
} from "../lib/backend";
import { getErrorMessage } from "../lib/errors";
import { supabase } from "../lib/supabase";
import type { CandidateReviewStatus, CrisisCase, SourceCandidate, SourceDiscoveryJobResponse, SourceTopic } from "../lib/types";
import { useI18n } from "../lib/i18n";

const REVIEW_COLORS: Record<CandidateReviewStatus, "background-frosted" | "notification-success-soft" | "notification-error-soft"> = {
  pending: "background-frosted",
  accepted: "notification-success-soft",
  rejected: "notification-error-soft",
};

export default function CandidateSourcesReviewPage() {
  const { t } = useI18n();
  const { caseId, jobId } = useParams<{ caseId: string; jobId: string }>();
  const navigate = useNavigate();
  const [crisisCase, setCrisisCase] = useState<CrisisCase | null>(null);
  const [job, setJob] = useState<SourceDiscoveryJobResponse | null>(null);
  const [candidates, setCandidates] = useState<SourceCandidate[]>([]);
  const [topics, setTopics] = useState<SourceTopic[]>([]);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState("");
  const [savingLibraryId, setSavingLibraryId] = useState("");
  const [creatingPack, setCreatingPack] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [candidateTopicSelections, setCandidateTopicSelections] = useState<Record<string, string>>({});

  const fetchPageData = useCallback(async () => {
    if (!caseId || !jobId) return;
    const [{ data }, jobResponse, candidateResponse, topicResponse] = await Promise.all([
      supabase.from("crisis_cases").select("*").eq("id", caseId).maybeSingle(),
      fetchSourceDiscoveryJob(jobId),
      fetchSourceCandidates({ discovery_job_id: jobId }),
      fetchSourceTopics(),
    ]);
    return { crisisCase: data, job: jobResponse, candidates: candidateResponse, topics: topicResponse };
  }, [caseId, jobId]);

  const load = useCallback(async () => {
    if (!caseId || !jobId) return;
    setLoading(true);
    try {
      const data = await fetchPageData();
      if (!data) return;
      setCrisisCase(data.crisisCase);
      setJob(data.job);
      setCandidates(data.candidates);
      setTopics(data.topics);
    } catch (error: unknown) {
      setError(getErrorMessage(error, "Failed to load source candidates."));
    }
    setLoading(false);
  }, [caseId, fetchPageData, jobId]);

  useEffect(() => {
    if (!caseId || !jobId) return undefined;
    let cancelled = false;

    async function runInitialLoad() {
      try {
        const data = await fetchPageData();
        if (cancelled || !data) return;
        setCrisisCase(data.crisisCase);
        setJob(data.job);
        setCandidates(data.candidates);
        setTopics(data.topics);
      } catch (error: unknown) {
        if (cancelled) return;
        setError(getErrorMessage(error, "Failed to load source candidates."));
      }
      if (!cancelled) {
        setLoading(false);
      }
    }

    void runInitialLoad();

    return () => {
      cancelled = true;
    };
  }, [caseId, fetchPageData, jobId]);

  useEffect(() => {
    if (!job?.should_poll || !jobId) return;
    const timeoutId = window.setTimeout(() => {
      void load();
    }, 2000);
    return () => window.clearTimeout(timeoutId);
  }, [job?.should_poll, jobId, load]);

  const acceptedCandidates = candidates.filter((candidate) => candidate.review_status === "accepted");
  const isFailed = job?.status === "failed" || job?.job_status === "failed";
  const statusColor = job?.should_poll
    ? "notification-warning-soft"
    : isFailed
      ? "notification-error-soft"
      : "notification-success-soft";

  async function updateReview(candidate: SourceCandidate, reviewStatus: CandidateReviewStatus) {
    setUpdatingId(candidate.id);
    setError("");
    setSuccess("");
    try {
      const updated = await updateSourceCandidateReview(candidate.id, reviewStatus);
      setCandidates((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      if (jobId) {
        setJob(await fetchSourceDiscoveryJob(jobId));
      }
    } catch (error: unknown) {
      setError(getErrorMessage(error, "Failed to update candidate review."));
    }
    setUpdatingId("");
  }

  async function saveCandidate(candidate: SourceCandidate) {
    setSavingLibraryId(candidate.id);
    setError("");
    setSuccess("");
    try {
      const topicId = candidateTopicSelections[candidate.id] || null;
      const response = await saveSourceCandidateToLibrary(candidate.id, {
        topic_id: topicId,
        reason: topicId ? "Saved from source candidate review." : "Saved from review as Unassigned.",
        assigned_by: "user",
      });
      setSuccess(response.topic_assignment_id ? "Candidate saved to the selected topic." : "Candidate saved as Unassigned.");
    } catch (error: unknown) {
      setError(getErrorMessage(error, "Failed to save candidate to the source library."));
    }
    setSavingLibraryId("");
  }

  async function createPack() {
    if (!caseId || !jobId) return;
    setCreatingPack(true);
    setError("");
    try {
      const response = await createEvidencePack({
        case_id: caseId,
        discovery_job_id: jobId,
        candidate_ids: acceptedCandidates.map((candidate) => candidate.id),
        title: `${crisisCase?.title || "Case"} evidence pack`,
      });
      navigate(`/cases/${caseId}/evidence-packs/${response.evidence_pack_id}`);
    } catch (error: unknown) {
      setError(getErrorMessage(error, "Failed to create evidence pack."));
    }
    setCreatingPack(false);
  }

  if (loading) {
    return <div className="flex items-center justify-center min-h-full"><PSpinner size="medium" /></div>;
  }

  return (
    <div className="min-h-full">
      <PageHeader
        title={t("candidate.title")}
        subtitle={crisisCase?.title}
        breadcrumbs={[
          { label: t("common.dashboard"), href: "/" },
          { label: crisisCase?.title || t("common.case"), href: `/cases/${caseId}/documents` },
          { label: t("discovery.title"), href: `/cases/${caseId}/source-discovery` },
          { label: t("candidate.review") },
        ]}
        action={job && <PTag color={statusColor}>{job.status}</PTag>}
      />

      <div className="p-fluid-lg w-full">
        {error && (
          <PInlineNotification heading={t("common.error")} description={error} state="error" dismissButton className="mb-fluid-md" onDismiss={() => setError("")} />
        )}
        {success && (
          <PInlineNotification heading={t("common.success")} description={success} state="success" dismissButton className="mb-fluid-md" onDismiss={() => setSuccess("")} />
        )}

        <div className="grid grid-cols-1 gap-fluid-md xl:grid-cols-5">
          <div className="flex flex-col gap-static-sm xl:col-span-3">
            {candidates.length === 0 ? (
              <div className="bg-surface border border-contrast-low rounded-lg p-fluid-xl flex flex-col items-center gap-static-md text-center">
                <PIcon name={isFailed ? "warning" : "document"} size="large" color="contrast-medium" />
                <PText className="text-contrast-medium">
                  {job?.should_poll
                    ? "Discovery is still running."
                    : isFailed
                      ? "Discovery failed before candidates could be written."
                      : "No candidates were found."}
                </PText>
                {isFailed && (
                  <div className="bg-canvas rounded p-static-sm max-w-full text-left">
                    <PText size="small" weight="semi-bold">
                      {job?.last_error_code || "SOURCE_DISCOVERY_ERROR"}
                    </PText>
                    <PText size="small" className="text-contrast-medium mt-static-xs">
                      {job?.last_error || "The worker did not provide an error message."}
                    </PText>
                  </div>
                )}
              </div>
            ) : candidates.map((candidate) => (
              <div key={candidate.id} className="bg-surface border border-contrast-low rounded-lg p-fluid-sm">
                <div className="flex flex-col gap-static-md lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0">
                    <div className="flex items-center gap-static-xs flex-wrap mb-static-xs">
                      <PTag color={REVIEW_COLORS[candidate.review_status]}>{candidate.review_status}</PTag>
                      <PTag color="background-frosted">{candidate.classification}</PTag>
                      <PTag color="notification-info-soft">{Math.round(candidate.total_score * 100)} score</PTag>
                      {candidate.semantic_support !== undefined && candidate.semantic_support !== null && (
                        <PTag color="notification-info-soft">{Math.round(candidate.semantic_support * 100)} semantic</PTag>
                      )}
                    </div>
                    <PHeading size="small">{candidate.title}</PHeading>
                    {candidate.url && (
                      <PText size="small" className="text-contrast-low truncate mt-static-xs">{candidate.url}</PText>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-static-xs shrink-0">
                    <PButton
                      variant={candidate.review_status === "accepted" ? "primary" : "secondary"}
                      loading={updatingId === candidate.id}
                      disabled={Boolean(updatingId)}
                      onClick={() => void updateReview(candidate, "accepted")}
                    >
                      {t("candidate.accept")}
                    </PButton>
                    <PButton
                      variant="secondary"
                      loading={updatingId === candidate.id}
                      disabled={Boolean(updatingId)}
                      onClick={() => void updateReview(candidate, "rejected")}
                    >
                      {t("candidate.reject")}
                    </PButton>
                  </div>
                </div>

                {candidate.review_status === "accepted" && (
                  <div className="mt-static-sm bg-canvas rounded p-static-sm flex flex-col gap-static-sm lg:flex-row lg:items-end">
                    <label className="flex flex-col gap-static-xs flex-1">
                      <PText size="small" weight="semi-bold">{t("candidate.saveToLibrary")}</PText>
                      <select
                        value={candidateTopicSelections[candidate.id] || ""}
                        onChange={(event) => setCandidateTopicSelections((current) => ({
                          ...current,
                          [candidate.id]: event.target.value,
                        }))}
                        className="w-full border border-contrast-low rounded bg-surface px-static-sm py-static-xs text-primary focus:outline-none focus:border-primary"
                        style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "14px" }}
                      >
                        <option value="">Unassigned</option>
                        {topics.map((topic) => (
                          <option key={topic.id} value={topic.id}>{topic.name}</option>
                        ))}
                      </select>
                    </label>
                    <PButton
                      variant="secondary"
                      loading={savingLibraryId === candidate.id}
                      disabled={Boolean(savingLibraryId)}
                      onClick={() => void saveCandidate(candidate)}
                    >
                      {t("common.save")}
                    </PButton>
                  </div>
                )}

                <PText size="small" className="text-contrast-medium mt-static-sm line-clamp-3">{candidate.excerpt}</PText>

                {Boolean(candidate.matched_fragments?.length) && (
                  <div className="mt-static-sm flex flex-col gap-static-xs">
                    {candidate.matched_fragments?.slice(0, 2).map((fragment) => (
                      <div key={fragment.id} className="bg-canvas rounded p-static-xs">
                        <PText size="x-small" className="text-contrast-medium">
                          {Math.round(fragment.similarity * 100)} match · fragment {fragment.fragment_index + 1}
                        </PText>
                        <PText size="small" className="text-contrast-medium line-clamp-2">{fragment.text}</PText>
                      </div>
                    ))}
                  </div>
                )}

                {Boolean(candidate.ranking_reasons?.length) && (
                  <div className="flex gap-static-xs flex-wrap mt-static-sm">
                    {candidate.ranking_reasons?.slice(0, 4).map((reason) => (
                      <PTag key={`${candidate.id}-${reason.key}`} color="background-frosted">{reason.label}: {reason.value}</PTag>
                    ))}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-static-xs mt-static-sm sm:grid-cols-3 2xl:grid-cols-6">
                  {Object.entries(candidate.scores).map(([key, value]) => (
                    <div key={key} className="bg-canvas rounded p-static-xs">
                      <PText size="x-small" className="text-contrast-medium">{key.replace("_", " ")}</PText>
                      <PText size="small" weight="semi-bold">{Math.round(value * 100)}</PText>
                    </div>
                  ))}
                </div>

                {(candidate.claim_previews.length > 0 || candidate.stakeholder_previews.length > 0) && (
                  <div className="grid grid-cols-1 gap-static-sm mt-static-sm lg:grid-cols-2">
                    <div>
                      <PText size="small" weight="semi-bold" className="mb-static-xs">{t("candidate.claims")}</PText>
                      <div className="flex flex-col gap-static-xs">
                        {candidate.claim_previews.slice(0, 2).map((claim, index) => (
                          <PText key={index} size="small" className="text-contrast-medium">{String(claim.text || "")}</PText>
                        ))}
                      </div>
                    </div>
                    <div>
                      <PText size="small" weight="semi-bold" className="mb-static-xs">{t("candidate.stakeholders")}</PText>
                      <div className="flex gap-static-xs flex-wrap">
                        {candidate.stakeholder_previews.slice(0, 5).map((stakeholder, index) => (
                          <PTag key={index} color="background-frosted">{String(stakeholder.name || "")}</PTag>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="xl:col-span-2">
            <div className="bg-surface border border-contrast-low rounded-lg p-fluid-md flex flex-col gap-fluid-sm xl:sticky xl:top-fluid-md">
              <PHeading size="small">Review Summary</PHeading>
              <div className="grid grid-cols-1 gap-static-xs sm:grid-cols-3 xl:grid-cols-1 2xl:grid-cols-3">
                <div className="bg-canvas rounded p-static-sm text-center">
                  <PText size="small" weight="semi-bold">{candidates.length}</PText>
                  <PText size="x-small" className="text-contrast-medium">Total</PText>
                </div>
                <div className="bg-canvas rounded p-static-sm text-center">
                  <PText size="small" weight="semi-bold">{acceptedCandidates.length}</PText>
                  <PText size="x-small" className="text-contrast-medium">Accepted</PText>
                </div>
                <div className="bg-canvas rounded p-static-sm text-center">
                  <PText size="small" weight="semi-bold">{candidates.filter((candidate) => candidate.review_status === "rejected").length}</PText>
                  <PText size="x-small" className="text-contrast-medium">Rejected</PText>
                </div>
              </div>

              {job?.should_poll && (
                <PText size="small" className="text-contrast-medium">The worker is still discovering sources. Candidate results refresh automatically.</PText>
              )}
              {isFailed && (
                <PInlineNotification
                  heading={job?.last_error_code || "Discovery failed"}
                  description={job?.last_error || "The worker failed before writing candidates."}
                  state="error"
                />
              )}

              <PButton
                icon="arrow-right"
                loading={creatingPack}
                disabled={creatingPack || acceptedCandidates.length === 0}
                onClick={createPack}
              >
                Create Evidence Pack
              </PButton>
              <PButton variant="secondary" onClick={() => navigate(`/cases/${caseId}/source-discovery`)}>
                New Discovery
              </PButton>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
