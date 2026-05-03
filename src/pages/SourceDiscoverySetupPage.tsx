import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  PButton, PHeading, PInlineNotification, PSpinner, PTag, PText,
} from "@porsche-design-system/components-react";
import PageHeader from "../components/PageHeader";
import SourceDiscoveryAssistantPanel from "../components/SourceDiscoveryAssistantPanel";
import StatusBadge from "../components/StatusBadge";
import { createSourceDiscoveryJob } from "../lib/backend";
import { getErrorMessage } from "../lib/errors";
import { supabase } from "../lib/supabase";
import type {
  CrisisCase,
  SourceDiscoveryAssistantPlanningSuggestion,
  SourceDiscoveryAssistantRecommendedSettings,
  SourceDiscoveryAssistantResponse,
  SourceDiscoveryPlanningContext,
} from "../lib/types";
import { useI18n } from "../lib/i18n";

const SOURCE_TYPES = ["news", "official", "social", "complaint", "research"];
const TIME_RANGE_PRESETS = [
  { value: "last_24_hours", label: "Last 24 hours" },
  { value: "last_7_days", label: "Last 7 days" },
  { value: "last_30_days", label: "Last 30 days" },
  { value: "last_90_days", label: "Last 90 days" },
  { value: "last_365_days", label: "Last year" },
  { value: "anytime", label: "Any time" },
];

function appendUnique(values: string[], nextValues: readonly string[] | undefined) {
  for (const value of nextValues ?? []) {
    const normalized = value.trim();
    if (normalized && !values.includes(normalized)) {
      values.push(normalized);
    }
  }
}

function buildPlanningContext(response: SourceDiscoveryAssistantResponse | null | undefined): SourceDiscoveryPlanningContext | null {
  if (!response) return null;

  const context: SourceDiscoveryPlanningContext = {
    core_entities: [],
    actor_names: [],
    event_aliases: [],
    language_variants: [],
    evidence_buckets: [],
  };

  const addFrom = (item: SourceDiscoveryAssistantPlanningSuggestion | SourceDiscoveryAssistantRecommendedSettings | null) => {
    if (!item) return;
    appendUnique(context.core_entities, item.core_entities);
    appendUnique(context.actor_names, item.actor_names);
    appendUnique(context.event_aliases, item.event_aliases);
    appendUnique(context.language_variants, item.language_variants);
    for (const bucket of item.evidence_buckets ?? []) {
      if (!context.evidence_buckets.some((current) => current.key === bucket.key)) {
        context.evidence_buckets.push(bucket);
      }
    }
  };

  addFrom(response.recommended_settings);
  response.planning_suggestions.forEach(addFrom);

  return (
    context.core_entities.length
    || context.actor_names.length
    || context.event_aliases.length
    || context.language_variants.length
    || context.evidence_buckets.length
  ) ? context : null;
}

export default function SourceDiscoverySetupPage() {
  const { t } = useI18n();
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
        planning_context: buildPlanningContext(crisisCase?.source_discovery_assistant_response),
      });
      navigate(`/cases/${caseId}/source-discovery/${response.source_discovery_job_id}/review`);
    } catch (error: unknown) {
      setError(getErrorMessage(error, "Failed to create source discovery job."));
    }
    setSubmitting(false);
  }

  function applyAssistantSuggestion(
    suggestion: SourceDiscoveryAssistantPlanningSuggestion | SourceDiscoveryAssistantRecommendedSettings,
  ) {
    if (suggestion.topic) setTopic(suggestion.topic);
    if (suggestion.description) setDescription(suggestion.description);
    if (suggestion.region) setRegion(suggestion.region);
    if (suggestion.language) setLanguage(suggestion.language);
    if (suggestion.time_range) setTimeRange(suggestion.time_range);
    if (suggestion.source_types.length > 0) setSourceTypes(suggestion.source_types);
    if ("max_sources" in suggestion && suggestion.max_sources) setMaxSources(suggestion.max_sources);
  }

  async function persistAssistantResponse(response: SourceDiscoveryAssistantResponse) {
    if (!caseId) return;

    const { error: updateError } = await supabase
      .from("crisis_cases")
      .update({
        source_discovery_assistant_response: response,
        source_discovery_assistant_updated_at: new Date().toISOString(),
      })
      .eq("id", caseId);

    if (updateError) {
      throw updateError;
    }

    setCrisisCase((currentCase) => (
      currentCase
        ? {
          ...currentCase,
          source_discovery_assistant_response: response,
          source_discovery_assistant_updated_at: new Date().toISOString(),
        }
        : currentCase
    ));
  }

  if (loading) {
    return <div className="flex items-center justify-center min-h-full"><PSpinner size="medium" /></div>;
  }

  return (
    <div className="min-h-full">
      <PageHeader
        title={t("discovery.title")}
        subtitle={crisisCase?.title}
        breadcrumbs={[
          { label: t("common.dashboard"), href: "/" },
          { label: crisisCase?.title || t("common.case"), href: `/cases/${caseId}/documents` },
          { label: t("discovery.title") },
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

        <div className="grid grid-cols-1 gap-fluid-md xl:grid-cols-5">
          <div className="xl:col-span-3">
            <div className="bg-surface border border-contrast-low rounded-lg p-fluid-md flex flex-col gap-fluid-md">
          <div>
            <PHeading size="small">{t("discovery.settings")}</PHeading>
            <PText size="small" className="text-contrast-medium mt-static-xs">
              {t("discovery.settingsDesc")}
            </PText>
          </div>

          <div className="grid grid-cols-1 gap-fluid-md lg:grid-cols-2">
            <label className="flex flex-col gap-static-xs lg:col-span-2">
              <PText size="small" weight="semi-bold">{t("discovery.topic")}</PText>
              <input
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
                className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary focus:outline-none focus:border-primary"
                style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
              />
            </label>

            <label className="flex flex-col gap-static-xs lg:col-span-2">
              <PText size="small" weight="semi-bold">{t("discovery.description")}</PText>
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={5}
                className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary focus:outline-none focus:border-primary resize-none"
                style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
              />
            </label>

            <label className="flex flex-col gap-static-xs">
              <PText size="small" weight="semi-bold">{t("discovery.region")}</PText>
              <input
                value={region}
                onChange={(event) => setRegion(event.target.value)}
                placeholder="e.g. United States, EU, Global"
                className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary placeholder:text-contrast-low focus:outline-none focus:border-primary"
                style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
              />
            </label>

            <label className="flex flex-col gap-static-xs">
              <PText size="small" weight="semi-bold">{t("discovery.language")}</PText>
              <input
                value={language}
                onChange={(event) => setLanguage(event.target.value)}
                className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary focus:outline-none focus:border-primary"
                style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
              />
            </label>

            <label className="flex flex-col gap-static-xs">
              <PText size="small" weight="semi-bold">{t("discovery.timeRange")}</PText>
              <input
                list="source-discovery-time-ranges"
                value={timeRange}
                onChange={(event) => setTimeRange(event.target.value)}
                placeholder="last_90_days or 2026-04-01to2026-04-30"
                className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary focus:outline-none focus:border-primary"
                style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
              />
              <datalist id="source-discovery-time-ranges">
                {TIME_RANGE_PRESETS.map((preset) => (
                  <option key={preset.value} value={preset.value}>{preset.label}</option>
                ))}
              </datalist>
            </label>

            <label className="flex flex-col gap-static-xs">
              <PText size="small" weight="semi-bold">{t("discovery.maxSources")}</PText>
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
            <PText size="small" weight="semi-bold" className="mb-static-xs">{t("discovery.sourceTypes")}</PText>
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
              {t("discovery.createJob")}
            </PButton>
            <PButton variant="secondary" onClick={() => navigate(`/cases/${caseId}/documents`)}>
              {t("common.back")}
            </PButton>
          </div>
            </div>
          </div>

          <div className="xl:col-span-2">
            <SourceDiscoveryAssistantPanel
              key={caseId}
              title="LLM Source Assistant"
              description="Generate non-search planning guidance, or explicitly research a preliminary timeline with bounded searched sources."
              defaultQuestion="Help me generate search directions, keywords, source types, and a starting time range for this event."
              primaryActionLabel="Generate Search Plan"
              buildRequest={(question) => ({
                mode: "search_planning",
                question,
                case_id: caseId,
                topic,
                description,
                region,
                language,
                time_range: timeRange,
                source_types: sourceTypes,
                max_sources: maxSources,
              })}
              briefingQuestion="Research an initial timeline, key actors, controversy focus, source landscape, evidence gaps, and recommended discovery settings for this topic."
              buildBriefingRequest={(question) => ({
                mode: "search_backed_briefing",
                question,
                case_id: caseId,
                topic,
                description,
                region,
                language,
                time_range: timeRange,
                source_types: sourceTypes,
                max_sources: maxSources,
              })}
              initialResponse={crisisCase?.source_discovery_assistant_response ?? null}
              onResponse={persistAssistantResponse}
              onApplySuggestion={applyAssistantSuggestion}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
