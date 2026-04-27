import type { ComponentProps } from "react";
import { useCallback, useEffect, useState } from "react";
import {
  PButton, PButtonPure, PHeading, PIcon, PInlineNotification, PSpinner, PTag, PText,
} from "@porsche-design-system/components-react";
import PageHeader from "../components/PageHeader";
import {
  createSourceTopic,
  createSourceTopicAssignment,
  fetchSourceRegistry,
  fetchSourceTopics,
  fetchSourceUsage,
  removeSourceTopicAssignment,
} from "../lib/backend";
import { getErrorMessage } from "../lib/errors";
import type { SourceRegistrySource, SourceTopic, SourceUsageResponse } from "../lib/types";

type TagColor = NonNullable<ComponentProps<typeof PTag>["color"]>;

const SMART_VIEWS = [
  { key: "unassigned", label: "Unassigned", desc: "Needs topic cleanup" },
  { key: "recently_used", label: "Recently Used", desc: "Already reused in cases" },
  { key: "high_authority", label: "High Authority", desc: "Official or trusted sources" },
  { key: "duplicate_candidates", label: "Duplicate Candidates", desc: "Same URL or content hash" },
  { key: "stale", label: "Stale Sources", desc: "Needs freshness review" },
];

const SOURCE_KINDS = ["", "news", "official", "complaint", "social", "research"];
const AUTHORITY_LEVELS = ["", "high", "medium", "low"];
const FRESHNESS_STATUSES = ["", "current", "stale", "unknown"];
const SOURCE_STATUSES = ["", "active", "duplicate_candidate", "stale", "archived"];

type View =
  | { type: "all" }
  | { type: "smart"; key: string }
  | { type: "topic"; topicId: string };

function tagColor(value: string): TagColor {
  if (value === "official" || value === "high" || value === "active") return "notification-success-soft";
  if (value === "stale" || value === "duplicate_candidate") return "notification-warning-soft";
  if (value === "complaint" || value === "social" || value === "low") return "notification-error-soft";
  return "background-frosted";
}

function viewKey(view: View): string {
  if (view.type === "all") return "all";
  if (view.type === "smart") return `smart:${view.key}`;
  return `topic:${view.topicId}`;
}

export default function GlobalSourcesPage() {
  const [topics, setTopics] = useState<SourceTopic[]>([]);
  const [sources, setSources] = useState<SourceRegistrySource[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState("");
  const [usage, setUsage] = useState<SourceUsageResponse | null>(null);
  const [view, setView] = useState<View>({ type: "smart", key: "unassigned" });
  const [loading, setLoading] = useState(true);
  const [usageLoading, setUsageLoading] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [showTopicForm, setShowTopicForm] = useState(false);
  const [topicName, setTopicName] = useState("");
  const [topicType, setTopicType] = useState("collection");
  const [query, setQuery] = useState("");
  const [sourceKind, setSourceKind] = useState("");
  const [authorityLevel, setAuthorityLevel] = useState("");
  const [freshnessStatus, setFreshnessStatus] = useState("");
  const [sourceStatus, setSourceStatus] = useState("");
  const [assignTopicId, setAssignTopicId] = useState("");
  const [assignReason, setAssignReason] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const selectedSource = sources.find((source) => source.id === selectedSourceId) || sources[0] || null;

  const loadTopics = useCallback(async () => {
    setTopics(await fetchSourceTopics());
  }, []);

  const loadSources = useCallback(async () => {
    const response = await fetchSourceRegistry({
      topic_id: view.type === "topic" ? view.topicId : undefined,
      smart_view: view.type === "smart" ? view.key : undefined,
      query: query.trim() || undefined,
      source_kind: sourceKind || undefined,
      authority_level: authorityLevel || undefined,
      freshness_status: freshnessStatus || undefined,
      source_status: sourceStatus || undefined,
    });
    setSources(response.sources);
    setSelectedSourceId((current) => {
      if (current && response.sources.some((source) => source.id === current)) return current;
      return response.sources[0]?.id || "";
    });
  }, [authorityLevel, freshnessStatus, query, sourceKind, sourceStatus, view]);

  useEffect(() => {
    let cancelled = false;

    async function runInitialLoad() {
      setLoading(true);
      try {
        const [topicRows, registry] = await Promise.all([
          fetchSourceTopics(),
          fetchSourceRegistry({ smart_view: "unassigned" }),
        ]);
        if (cancelled) return;
        setTopics(topicRows);
        setSources(registry.sources);
        setSelectedSourceId(registry.sources[0]?.id || "");
      } catch (requestError: unknown) {
        if (!cancelled) setError(getErrorMessage(requestError, "Failed to load source registry."));
      }
      if (!cancelled) setLoading(false);
    }

    void runInitialLoad();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (loading) return undefined;
    let cancelled = false;

    async function refreshSources() {
      try {
        await loadSources();
      } catch (requestError: unknown) {
        if (!cancelled) setError(getErrorMessage(requestError, "Failed to refresh source registry."));
      }
    }

    void refreshSources();

    return () => {
      cancelled = true;
    };
  }, [loadSources, loading]);

  useEffect(() => {
    if (!selectedSource) {
      return undefined;
    }
    let cancelled = false;

    async function loadUsage() {
      setUsageLoading(true);
      try {
        const response = await fetchSourceUsage(selectedSource.id);
        if (!cancelled) setUsage(response);
      } catch (requestError: unknown) {
        if (!cancelled) setError(getErrorMessage(requestError, "Failed to load source usage."));
      }
      if (!cancelled) setUsageLoading(false);
    }

    void loadUsage();

    return () => {
      cancelled = true;
    };
  }, [selectedSource]);

  async function addTopic() {
    if (!topicName.trim()) {
      setError("Topic name is required.");
      return;
    }
    setError("");
    setSuccess("");
    try {
      await createSourceTopic({ name: topicName.trim(), topic_type: topicType });
      setTopicName("");
      setTopicType("collection");
      setShowTopicForm(false);
      await loadTopics();
      setSuccess("Topic created.");
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError, "Failed to create source topic."));
    }
  }

  async function assignSelectedSource() {
    if (!selectedSource || !assignTopicId) {
      setError("Select a source and topic before assigning.");
      return;
    }
    setAssigning(true);
    setError("");
    setSuccess("");
    try {
      await createSourceTopicAssignment({
        global_source_id: selectedSource.id,
        topic_id: assignTopicId,
        reason: assignReason.trim(),
        assigned_by: "user",
      });
      setAssignReason("");
      await loadSources();
      setSuccess("Source assigned to topic.");
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError, "Failed to assign source to topic."));
    }
    setAssigning(false);
  }

  async function removeAssignment(assignmentId: string) {
    setError("");
    setSuccess("");
    try {
      await removeSourceTopicAssignment(assignmentId);
      await loadSources();
      setSuccess("Source removed from topic.");
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError, "Failed to remove topic assignment."));
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center min-h-full"><PSpinner size="medium" /></div>;
  }

  return (
    <div className="min-h-full">
      <PageHeader
        title="Global Source Library"
        subtitle="Organize reusable source material by topic, maintenance view, and usage context."
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Source Library" }]}
        action={(
          <PButton icon="add" onClick={() => setShowTopicForm((current) => !current)}>
            New Topic
          </PButton>
        )}
      />

      <div className="p-fluid-lg w-full flex flex-col gap-fluid-md">
        {error && (
          <PInlineNotification heading="Error" description={error} state="error" dismissButton onDismiss={() => setError("")} />
        )}
        {success && (
          <PInlineNotification heading="Success" description={success} state="success" dismissButton onDismiss={() => setSuccess("")} />
        )}

        {showTopicForm && (
          <div className="bg-surface border border-contrast-low rounded-lg p-fluid-md grid grid-cols-1 gap-static-sm items-end md:grid-cols-2 xl:grid-cols-5">
            <label className="flex flex-col gap-static-xs md:col-span-2">
              <PText size="small" weight="semi-bold">Topic Name</PText>
              <input
                value={topicName}
                onChange={(event) => setTopicName(event.target.value)}
                className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary focus:outline-none focus:border-primary"
                style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
              />
            </label>
            <label className="flex flex-col gap-static-xs">
              <PText size="small" weight="semi-bold">Type</PText>
              <select
                value={topicType}
                onChange={(event) => setTopicType(event.target.value)}
                className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary focus:outline-none focus:border-primary"
                style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
              >
                <option value="collection">Collection</option>
                <option value="crisis">Crisis</option>
                <option value="product">Product</option>
                <option value="region">Region</option>
                <option value="stakeholder">Stakeholder</option>
              </select>
            </label>
            <PButton disabled={!topicName.trim()} onClick={addTopic}>Create Topic</PButton>
            <PButton variant="secondary" onClick={() => setShowTopicForm(false)}>Cancel</PButton>
          </div>
        )}

        <div className="grid grid-cols-1 gap-fluid-md items-start xl:grid-cols-6">
          <aside className="bg-surface border border-contrast-low rounded-lg p-static-sm flex flex-col gap-static-md xl:col-span-1">
            <div>
              <PText size="small" weight="semi-bold" className="mb-static-xs">Smart Views</PText>
              <div className="flex flex-wrap gap-static-xs xl:flex-col">
                <button
                  className={`text-left rounded px-static-sm py-static-xs ${viewKey(view) === "all" ? "bg-primary text-[white]" : "hover:bg-canvas"}`}
                  onClick={() => setView({ type: "all" })}
                >
                  All Sources
                </button>
                {SMART_VIEWS.map((smartView) => (
                  <button
                    key={smartView.key}
                    className={`text-left rounded px-static-sm py-static-xs ${viewKey(view) === `smart:${smartView.key}` ? "bg-primary text-[white]" : "hover:bg-canvas"}`}
                    onClick={() => setView({ type: "smart", key: smartView.key })}
                  >
                    <span className="block text-sm">{smartView.label}</span>
                    <span className="block text-xs opacity-70">{smartView.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <PText size="small" weight="semi-bold" className="mb-static-xs">Topics</PText>
              <div className="flex flex-wrap gap-static-xs max-h-[420px] overflow-auto pr-static-xs xl:flex-col">
                {topics.map((topic) => (
                  <button
                    key={topic.id}
                    className={`text-left rounded px-static-sm py-static-xs ${viewKey(view) === `topic:${topic.id}` ? "bg-primary text-[white]" : "hover:bg-canvas"}`}
                    onClick={() => setView({ type: "topic", topicId: topic.id })}
                  >
                    <span className="block text-sm">{topic.name}</span>
                    <span className="block text-xs opacity-70">{topic.topic_type}</span>
                  </button>
                ))}
              </div>
            </div>
          </aside>

          <section className="bg-surface border border-contrast-low rounded-lg overflow-hidden xl:col-span-3">
            <div className="p-fluid-md border-b border-contrast-low grid grid-cols-1 gap-static-sm sm:grid-cols-2 2xl:grid-cols-5">
              <label className="flex flex-col gap-static-xs sm:col-span-2 2xl:col-span-5">
                <PText size="small" weight="semi-bold">Search Registry</PText>
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search title, content, or source kind..."
                  className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary placeholder:text-contrast-low focus:outline-none focus:border-primary"
                  style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
                />
              </label>
              {[
                ["Kind", sourceKind, setSourceKind, SOURCE_KINDS],
                ["Authority", authorityLevel, setAuthorityLevel, AUTHORITY_LEVELS],
                ["Freshness", freshnessStatus, setFreshnessStatus, FRESHNESS_STATUSES],
                ["Status", sourceStatus, setSourceStatus, SOURCE_STATUSES],
              ].map(([label, value, setter, options]) => (
                <label key={String(label)} className="flex flex-col gap-static-xs">
                  <PText size="small" weight="semi-bold">{String(label)}</PText>
                  <select
                    value={String(value)}
                    onChange={(event) => (setter as (value: string) => void)(event.target.value)}
                    className="w-full border border-contrast-low rounded bg-canvas px-static-sm py-static-xs text-primary focus:outline-none focus:border-primary"
                    style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "14px" }}
                  >
                    {(options as string[]).map((option) => (
                      <option key={option || "any"} value={option}>{option || "Any"}</option>
                    ))}
                  </select>
                </label>
              ))}
              <div className="flex items-end">
                <PButton variant="secondary" className="w-full" onClick={() => void loadSources()}>
                  Refresh
                </PButton>
              </div>
            </div>

            {sources.length === 0 ? (
              <div className="p-fluid-lg flex flex-col items-center gap-static-sm text-center">
                <PIcon name="document" size="large" color="contrast-medium" />
                <PText className="text-contrast-medium">No sources match the current view.</PText>
              </div>
            ) : (
              <div className="divide-y divide-contrast-low">
                {sources.map((source) => (
                  <button
                    key={source.id}
                    className={`w-full text-left p-fluid-sm hover:bg-canvas ${selectedSource?.id === source.id ? "bg-canvas" : ""}`}
                    onClick={() => setSelectedSourceId(source.id)}
                  >
                    <div className="flex items-center gap-static-xs flex-wrap mb-static-xs">
                      <PTag color={tagColor(source.source_kind)}>{source.source_kind}</PTag>
                      <PTag color={tagColor(source.authority_level)}>{source.authority_level}</PTag>
                      <PTag color={tagColor(source.freshness_status)}>{source.freshness_status}</PTag>
                      {source.duplicate_candidate && <PTag color="notification-warning-soft">duplicate</PTag>}
                      {source.usage_count > 0 && <PTag color="notification-info-soft">{source.usage_count} uses</PTag>}
                    </div>
                    <PText size="small" weight="semi-bold" className="mb-static-xs">{source.title}</PText>
                    <PText size="small" className="text-contrast-medium line-clamp-3">{source.content}</PText>
                    <div className="flex gap-static-xs flex-wrap mt-static-xs">
                      {source.topic_assignments.slice(0, 3).map((assignment) => (
                        <PTag key={assignment.assignment_id} color="background-frosted">{assignment.topic_name}</PTag>
                      ))}
                      {source.topic_assignments.length === 0 && <PTag color="notification-warning-soft">Unassigned</PTag>}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </section>

          <aside className="bg-surface border border-contrast-low rounded-lg p-fluid-md xl:col-span-2 xl:sticky xl:top-fluid-md">
            {!selectedSource ? (
              <div className="flex flex-col items-center gap-static-sm text-center p-fluid-md">
                <PIcon name="document" size="large" color="contrast-medium" />
                <PText className="text-contrast-medium">Select a source to inspect details.</PText>
              </div>
            ) : (
              <div className="flex flex-col gap-fluid-sm">
                <div>
                  <PHeading size="small">{selectedSource.title}</PHeading>
                  <PText size="small" className="text-contrast-medium mt-static-xs line-clamp-5">{selectedSource.content}</PText>
                </div>

                <div className="grid grid-cols-1 gap-static-xs sm:grid-cols-3 xl:grid-cols-1 2xl:grid-cols-3">
                  <div className="bg-canvas rounded p-static-xs text-center">
                    <PText size="small" weight="semi-bold">{selectedSource.usage_count}</PText>
                    <PText size="x-small" className="text-contrast-medium">Uses</PText>
                  </div>
                  <div className="bg-canvas rounded p-static-xs text-center">
                    <PText size="small" weight="semi-bold">{selectedSource.topic_assignments.length}</PText>
                    <PText size="x-small" className="text-contrast-medium">Topics</PText>
                  </div>
                  <div className="bg-canvas rounded p-static-xs text-center">
                    <PText size="small" weight="semi-bold">{selectedSource.duplicate_candidate ? "Yes" : "No"}</PText>
                    <PText size="x-small" className="text-contrast-medium">Duplicate</PText>
                  </div>
                </div>

                <div>
                  <PText size="small" weight="semi-bold" className="mb-static-xs">Assign to Topic</PText>
                  <div className="flex flex-col gap-static-xs sm:flex-row">
                    <select
                      value={assignTopicId}
                      onChange={(event) => setAssignTopicId(event.target.value)}
                      className="flex-1 border border-contrast-low rounded bg-canvas px-static-sm py-static-xs text-primary focus:outline-none focus:border-primary"
                      style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "14px" }}
                    >
                      <option value="">Select topic</option>
                      {topics.map((topic) => (
                        <option key={topic.id} value={topic.id}>{topic.name}</option>
                      ))}
                    </select>
                    <PButton loading={assigning} disabled={assigning || !assignTopicId} onClick={assignSelectedSource}>
                      Assign
                    </PButton>
                  </div>
                  <input
                    value={assignReason}
                    onChange={(event) => setAssignReason(event.target.value)}
                    placeholder="Reason..."
                    className="w-full border border-contrast-low rounded bg-canvas px-static-sm py-static-xs text-primary placeholder:text-contrast-low focus:outline-none focus:border-primary mt-static-xs"
                    style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "14px" }}
                  />
                </div>

                <div>
                  <PText size="small" weight="semi-bold" className="mb-static-xs">Topic Assignments</PText>
                  <div className="flex flex-col gap-static-xs">
                    {selectedSource.topic_assignments.length === 0 ? (
                      <PText size="small" className="text-contrast-medium">No active topic assignments.</PText>
                    ) : selectedSource.topic_assignments.map((assignment) => (
                      <div key={assignment.assignment_id} className="bg-canvas rounded p-static-xs flex items-start justify-between gap-static-xs">
                        <div>
                          <PText size="small" weight="semi-bold">{assignment.topic_name}</PText>
                          <PText size="x-small" className="text-contrast-medium">{assignment.reason || assignment.assigned_by}</PText>
                        </div>
                        <PButtonPure icon="delete" onClick={() => void removeAssignment(assignment.assignment_id)} />
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <PText size="small" weight="semi-bold" className="mb-static-xs">Usage</PText>
                  {usageLoading ? (
                    <PSpinner size="small" />
                  ) : !usage || usage.cases.length === 0 ? (
                    <PText size="small" className="text-contrast-medium">Not used in any case yet.</PText>
                  ) : (
                    <div className="flex flex-col gap-static-xs">
                      {usage.cases.slice(0, 5).map((item) => (
                        <div key={item.source_document_id} className="bg-canvas rounded p-static-xs">
                          <PText size="small" weight="semi-bold">{item.case_title}</PText>
                          <PText size="x-small" className="text-contrast-medium">{item.source_origin}</PText>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </aside>
        </div>
      </div>
    </div>
  );
}
