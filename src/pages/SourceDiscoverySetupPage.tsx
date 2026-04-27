import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  PButton, PHeading, PInlineNotification, PSpinner, PTag, PText,
} from "@porsche-design-system/components-react";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import { createSourceDiscoveryJob } from "../lib/backend";
import { getErrorMessage } from "../lib/errors";
import { supabase } from "../lib/supabase";
import type { CrisisCase } from "../lib/types";

const SOURCE_TYPES = ["news", "official", "social", "complaint", "research"];

export default function SourceDiscoverySetupPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [crisisCase, setCrisisCase] = useState<CrisisCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [topic, setTopic] = useState("");
  const [description, setDescription] = useState("");
  const [region, setRegion] = useState("");
  const [language, setLanguage] = useState("en");
  const [timeRange, setTimeRange] = useState("last_30_days");
  const [sourceTypes, setSourceTypes] = useState<string[]>(["news", "official", "social"]);
  const [maxSources, setMaxSources] = useState(12);

  useEffect(() => {
    if (!caseId) return undefined;
    let cancelled = false;

    async function runInitialLoad() {
      const { data } = await supabase.from("crisis_cases").select("*").eq("id", caseId!).maybeSingle();
      if (cancelled) return;
      setCrisisCase(data);
      setTopic(data?.title ?? "");
      setDescription(data?.description ?? "");
      setLoading(false);
    }

    void runInitialLoad();

    return () => {
      cancelled = true;
    };
  }, [caseId]);

  function toggleSourceType(value: string) {
    setSourceTypes((current) => (
      current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value]
    ));
  }

  async function submit() {
    if (!caseId || !topic.trim()) {
      setError("Topic is required.");
      return;
    }
    if (sourceTypes.length === 0) {
      setError("Select at least one source type.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      const response = await createSourceDiscoveryJob({
        case_id: caseId,
        topic: topic.trim(),
        description: description.trim(),
        region: region.trim(),
        language: language.trim() || "en",
        time_range: timeRange,
        source_types: sourceTypes,
        max_sources: maxSources,
      });
      navigate(`/cases/${caseId}/source-discovery/${response.source_discovery_job_id}/review`);
    } catch (error: unknown) {
      setError(getErrorMessage(error, "Failed to create source discovery job."));
    }
    setSubmitting(false);
  }

  if (loading) {
    return <div className="flex items-center justify-center min-h-full"><PSpinner size="medium" /></div>;
  }

  return (
    <div className="min-h-full">
      <PageHeader
        title="Source Discovery"
        subtitle={crisisCase?.title}
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: crisisCase?.title || "Case", href: `/cases/${caseId}/documents` },
          { label: "Source Discovery" },
        ]}
        action={crisisCase && <StatusBadge status={crisisCase.status} />}
      />

      <div className="p-fluid-lg w-full">
        {error && (
          <PInlineNotification
            heading="Error"
            description={error}
            state="error"
            dismissButton
            className="mb-fluid-md"
            onDismiss={() => setError("")}
          />
        )}

        <div className="bg-surface border border-contrast-low rounded-lg p-fluid-md flex flex-col gap-fluid-md">
          <div>
            <PHeading size="small">Discovery Settings</PHeading>
            <PText size="small" className="text-contrast-medium mt-static-xs">
              Configure the topic and source boundaries before the worker builds candidate evidence.
            </PText>
          </div>

          <div className="grid grid-cols-1 gap-fluid-md lg:grid-cols-2">
            <label className="flex flex-col gap-static-xs lg:col-span-2">
              <PText size="small" weight="semi-bold">Topic *</PText>
              <input
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
                className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary focus:outline-none focus:border-primary"
                style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
              />
            </label>

            <label className="flex flex-col gap-static-xs lg:col-span-2">
              <PText size="small" weight="semi-bold">Description</PText>
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={5}
                className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary focus:outline-none focus:border-primary resize-none"
                style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
              />
            </label>

            <label className="flex flex-col gap-static-xs">
              <PText size="small" weight="semi-bold">Region</PText>
              <input
                value={region}
                onChange={(event) => setRegion(event.target.value)}
                placeholder="e.g. United States, EU, Global"
                className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary placeholder:text-contrast-low focus:outline-none focus:border-primary"
                style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
              />
            </label>

            <label className="flex flex-col gap-static-xs">
              <PText size="small" weight="semi-bold">Language</PText>
              <input
                value={language}
                onChange={(event) => setLanguage(event.target.value)}
                className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary focus:outline-none focus:border-primary"
                style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
              />
            </label>

            <label className="flex flex-col gap-static-xs">
              <PText size="small" weight="semi-bold">Time Range</PText>
              <select
                value={timeRange}
                onChange={(event) => setTimeRange(event.target.value)}
                className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary focus:outline-none focus:border-primary"
                style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
              >
                <option value="last_7_days">Last 7 days</option>
                <option value="last_30_days">Last 30 days</option>
                <option value="last_90_days">Last 90 days</option>
                <option value="anytime">Any time</option>
              </select>
            </label>

            <label className="flex flex-col gap-static-xs">
              <PText size="small" weight="semi-bold">Max Sources</PText>
              <input
                type="number"
                min={1}
                max={50}
                value={maxSources}
                onChange={(event) => setMaxSources(Number(event.target.value))}
                className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary focus:outline-none focus:border-primary"
                style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
              />
            </label>
          </div>

          <div>
            <PText size="small" weight="semi-bold" className="mb-static-xs">Source Types</PText>
            <div className="flex flex-wrap gap-static-sm">
              {SOURCE_TYPES.map((type) => (
                <button
                  key={type}
                  onClick={() => toggleSourceType(type)}
                  className={`px-static-md py-static-xs rounded border text-sm transition-colors ${
                    sourceTypes.includes(type)
                      ? "border-primary bg-primary text-[white]"
                      : "border-contrast-low bg-canvas text-contrast-medium hover:border-primary hover:text-primary"
                  }`}
                  style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif" }}
                >
                  {type}
                </button>
              ))}
            </div>
            <div className="flex gap-static-xs flex-wrap mt-static-sm">
              {sourceTypes.map((type) => <PTag key={type} color="background-frosted">{type}</PTag>)}
            </div>
          </div>

          <div className="border-t border-contrast-low pt-fluid-sm flex flex-wrap gap-static-sm">
            <PButton loading={submitting} disabled={submitting || !topic.trim()} icon="arrow-right" onClick={submit}>
              Create Discovery Job
            </PButton>
            <PButton variant="secondary" onClick={() => navigate(`/cases/${caseId}/documents`)}>
              Back
            </PButton>
          </div>
        </div>
      </div>
    </div>
  );
}
