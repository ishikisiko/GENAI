import type { ComponentProps } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  PButton, PButtonPure, PDivider, PHeading, PIcon, PInlineNotification, PSpinner, PTag, PText,
} from "@porsche-design-system/components-react";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import { DOC_TYPE_LABELS } from "../lib/constants";
import { getErrorMessage } from "../lib/errors";
import { requestBackend } from "../lib/backend";
import { supabase } from "../lib/supabase";
import type {
  CrisisCase,
  DocType,
  GlobalSourceDocument,
  GraphExtractionStatusResponse,
  GraphExtractionSubmissionResponse,
  SourceDocument,
  SourceOrigin,
} from "../lib/types";

type TagColor = NonNullable<ComponentProps<typeof PTag>["color"]>;

const DOC_TYPES: { value: DocType; label: string; desc: string; color: TagColor }[] = [
  { value: "news", label: "News Report", desc: "Media coverage or journalism", color: "notification-info-soft" },
  { value: "complaint", label: "User Complaint", desc: "Consumer feedback or complaint", color: "notification-warning-soft" },
  { value: "statement", label: "Official Statement", desc: "Corporate or government statement", color: "notification-success-soft" },
];

const ORIGIN_LABELS: Record<SourceOrigin, string> = {
  case_upload: "Uploaded in Case",
  global_library: "Added from Global Library",
};

const ORIGIN_COLORS: Record<SourceOrigin, TagColor> = {
  case_upload: "background-frosted",
  global_library: "notification-info-soft",
};

export default function DocumentsPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();

  const [crisisCase, setCrisisCase] = useState<CrisisCase | null>(null);
  const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [globalSources, setGlobalSources] = useState<GlobalSourceDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [extractionStatus, setExtractionStatus] = useState<GraphExtractionStatusResponse | null>(null);
  const [addingCaseUpload, setAddingCaseUpload] = useState(false);
  const [addingGlobalSources, setAddingGlobalSources] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedGlobalSourceIds, setSelectedGlobalSourceIds] = useState<string[]>([]);

  const [docTitle, setDocTitle] = useState("");
  const [docContent, setDocContent] = useState("");
  const [docType, setDocType] = useState<DocType>("news");

  const load = useCallback(async () => {
    setLoading(true);
    const [{ data: currentCase }, { data: docs }, { data: globals }] = await Promise.all([
      supabase.from("crisis_cases").select("*").eq("id", caseId!).maybeSingle(),
      supabase.from("source_documents").select("*").eq("case_id", caseId!).order("created_at"),
      supabase.from("global_source_documents").select("*").order("created_at", { ascending: false }),
    ]);

    setCrisisCase(currentCase);
    setDocuments(docs ?? []);
    setGlobalSources(globals ?? []);
    setLoading(false);
  }, [caseId]);

  useEffect(() => {
    if (caseId) void load();
  }, [caseId, load]);

  useEffect(() => {
    if (!extracting || !extractionStatus?.should_poll) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      void (async () => {
        try {
          const payload = await requestBackend<GraphExtractionStatusResponse>(
            `api/graph-extractions/${extractionStatus.job_id}`,
          );

          setExtractionStatus(payload);
          if (payload.should_poll) {
            return;
          }

          setExtracting(false);
          if (payload.status === "completed") {
            setSuccess(
              `Graph extracted: ${payload.entities_count} entities, ${payload.relations_count} relations, ${payload.claims_count} claims.`
            );
            await load();
            window.setTimeout(() => navigate(`/cases/${caseId}/grounding`), 1500);
            return;
          }

          setError(payload.last_error || "Extraction failed.");
        } catch (requestError: unknown) {
          setError(getErrorMessage(requestError, "Failed to refresh extraction status."));
          setExtracting(false);
        }
      })();
    }, 1500);

    return () => window.clearTimeout(timeoutId);
  }, [caseId, extracting, extractionStatus, load, navigate]);

  async function addCaseDocument() {
    if (!docContent.trim()) {
      setError("Document content is required.");
      return;
    }

    setAddingCaseUpload(true);
    setError("");
    setSuccess("");

    const payload = {
      title: docTitle.trim() || `${DOC_TYPE_LABELS[docType]} ${documents.length + 1}`,
      content: docContent.trim(),
      doc_type: docType,
    };

    const { data: globalDoc, error: globalError } = await supabase
      .from("global_source_documents")
      .insert(payload)
      .select()
      .maybeSingle();

    if (globalError || !globalDoc) {
      setError(globalError?.message || "Failed to sync the upload into the global library.");
      setAddingCaseUpload(false);
      return;
    }

    const { error: caseError } = await supabase.from("source_documents").insert({
      case_id: caseId!,
      global_source_id: globalDoc.id,
      source_origin: "case_upload",
      ...payload,
    });

    if (caseError) {
      await supabase.from("global_source_documents").delete().eq("id", globalDoc.id);
      setError(caseError.message);
      setAddingCaseUpload(false);
      return;
    }

    setDocTitle("");
    setDocContent("");
    setDocType("news");
    setShowUploadForm(false);
    setSuccess("Document added to this case and synced to the global library.");
    setAddingCaseUpload(false);
    await load();
  }

  async function addSelectedFromGlobalLibrary() {
    const selectedSources = globalSources.filter((source) =>
      selectedGlobalSourceIds.includes(source.id) && !linkedGlobalSourceIds.has(source.id)
    );

    if (selectedSources.length === 0) {
      setError("Select at least one global source.");
      return;
    }

    setAddingGlobalSources(true);
    setError("");
    setSuccess("");

    const { error: insertError } = await supabase.from("source_documents").insert(
      selectedSources.map((source) => ({
        case_id: caseId!,
        global_source_id: source.id,
        source_origin: "global_library",
        title: source.title,
        content: source.content,
        doc_type: source.doc_type,
      }))
    );

    if (insertError) {
      setError(insertError.message);
      setAddingGlobalSources(false);
      return;
    }

    setSelectedGlobalSourceIds([]);
    setSuccess(`Added ${selectedSources.length} global source${selectedSources.length > 1 ? "s" : ""} to this case.`);
    setAddingGlobalSources(false);
    await load();
  }

  function toggleGlobalSourceSelection(sourceId: string) {
    setSelectedGlobalSourceIds((current) =>
      current.includes(sourceId)
        ? current.filter((id) => id !== sourceId)
        : [...current, sourceId]
    );
  }

  async function deleteDocument(id: string) {
    setError("");
    setSuccess("");
    const { error: deleteError } = await supabase.from("source_documents").delete().eq("id", id);
    if (deleteError) {
      setError(deleteError.message);
      return;
    }
    setDocuments((current) => current.filter((doc) => doc.id !== id));
    setSuccess("Document removed from this case.");
  }

  async function extractGraph() {
    if (documents.length === 0) {
      setError("Add at least one document before extracting.");
      return;
    }
    setExtracting(true);
    setExtractionStatus(null);
    setError("");
    setSuccess("");

    try {
      const result = await requestBackend<GraphExtractionSubmissionResponse>("api/graph-extractions", {
        method: "POST",
        body: JSON.stringify({ case_id: caseId }),
      });
      setExtractionStatus({
        job_id: result.job_id,
        case_id: result.case_id,
        job_type: result.job_type,
        status: result.job_status,
        document_count: result.document_count,
        processed_documents: 0,
        failed_documents: 0,
        entities_count: 0,
        relations_count: 0,
        claims_count: 0,
        last_error: null,
        last_error_code: null,
        created_at: null,
        updated_at: null,
        should_poll: result.should_poll,
      });
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError, "Extraction failed."));
      setExtracting(false);
    }
  }

  const linkedGlobalSourceIds = useMemo(
    () => new Set(documents.map((doc) => doc.global_source_id).filter(Boolean)),
    [documents]
  );

  const filteredGlobalSources = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return globalSources;
    return globalSources.filter((source) =>
      source.title.toLowerCase().includes(normalized)
      || source.content.toLowerCase().includes(normalized)
      || DOC_TYPE_LABELS[source.doc_type].toLowerCase().includes(normalized)
    );
  }, [globalSources, query]);

  const selectedVisibleCount = useMemo(
    () => filteredGlobalSources.filter((source) => selectedGlobalSourceIds.includes(source.id)).length,
    [filteredGlobalSources, selectedGlobalSourceIds]
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-full">
        <PSpinner size="medium" />
      </div>
    );
  }

  return (
    <div className="min-h-full">
      <PageHeader
        title="Source Documents"
        subtitle={crisisCase?.title}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: crisisCase?.title || "Case", href: `/cases/${caseId}/documents` }, { label: "Documents" }]}
        action={crisisCase && <StatusBadge status={crisisCase.status} />}
      />

      <div className="p-fluid-lg max-w-6xl">
        {error && (
          <PInlineNotification heading="Error" description={error} state="error" dismissButton className="mb-fluid-md" onDismiss={() => setError("")} />
        )}
        {success && (
          <PInlineNotification heading="Success" description={success} state="success" dismissButton className="mb-fluid-md" onDismiss={() => setSuccess("")} />
        )}

        <div className="grid grid-cols-5 gap-fluid-md">
          <div className="col-span-3 flex flex-col gap-fluid-md">
            <div className="bg-surface border border-contrast-low rounded-lg overflow-hidden">
              <div className="px-fluid-md py-static-md border-b border-contrast-low flex items-center justify-between">
                <div>
                  <PHeading size="small">Case Documents</PHeading>
                  <PText size="small" className="text-contrast-medium">
                    Direct uploads are attached to this case and automatically synced into the global library.
                  </PText>
                </div>
                <PButtonPure icon="add" onClick={() => setShowUploadForm((current) => !current)}>
                  Add to Case
                </PButtonPure>
              </div>

              {showUploadForm && (
                <div className="p-fluid-md border-b border-contrast-low flex flex-col gap-fluid-sm">
                  <PHeading size="small">Upload Into This Case</PHeading>

                  <div>
                    <PText size="small" weight="semi-bold" className="mb-static-xs">Document Type</PText>
                    <div className="flex gap-static-sm flex-wrap">
                      {DOC_TYPES.map((type) => (
                        <button
                          key={type.value}
                          onClick={() => setDocType(type.value)}
                          className={`px-static-md py-static-xs rounded border text-sm transition-colors ${
                            docType === type.value
                              ? "border-primary bg-primary text-[white]"
                              : "border-contrast-low bg-canvas text-contrast-medium hover:border-primary hover:text-primary"
                          }`}
                          style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif" }}
                        >
                          {type.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <PText size="small" weight="semi-bold" className="mb-static-xs">Title (optional)</PText>
                    <input
                      value={docTitle}
                      onChange={(event) => setDocTitle(event.target.value)}
                      placeholder="Document title..."
                      className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary placeholder:text-contrast-low focus:outline-none focus:border-primary"
                      style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
                    />
                  </div>

                  <div>
                    <PText size="small" weight="semi-bold" className="mb-static-xs">Content *</PText>
                    <textarea
                      value={docContent}
                      onChange={(event) => setDocContent(event.target.value)}
                      placeholder="Paste the full document text here..."
                      rows={6}
                      className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary placeholder:text-contrast-low focus:outline-none focus:border-primary resize-none"
                      style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
                    />
                  </div>

                  <div className="flex gap-static-sm">
                    <PButton loading={addingCaseUpload} disabled={addingCaseUpload || !docContent.trim()} onClick={addCaseDocument}>
                      Add and Sync Globally
                    </PButton>
                    <PButton variant="secondary" onClick={() => setShowUploadForm(false)}>
                      Cancel
                    </PButton>
                  </div>
                </div>
              )}

              {documents.length === 0 ? (
                <div className="p-fluid-lg flex flex-col items-center gap-static-md text-center">
                  <PIcon name="document" size="large" color="contrast-medium" />
                  <PText className="text-contrast-medium">No documents in this case yet.</PText>
                  <PButton icon="add" variant="secondary" onClick={() => setShowUploadForm(true)}>
                    Add First Case Document
                  </PButton>
                </div>
              ) : (
                <div className="divide-y divide-contrast-low">
                  {documents.map((doc) => {
                    const typeConfig = DOC_TYPES.find((type) => type.value === doc.doc_type)!;
                    return (
                      <div key={doc.id} className="p-fluid-sm flex gap-static-md">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-static-sm mb-static-xs flex-wrap">
                            <PTag color={typeConfig.color}>{typeConfig.label}</PTag>
                            <PTag color={ORIGIN_COLORS[doc.source_origin]}>{ORIGIN_LABELS[doc.source_origin]}</PTag>
                            <PText size="small" className="text-contrast-low truncate">
                              {new Date(doc.created_at).toLocaleString()}
                            </PText>
                          </div>
                          <PText size="small" weight="semi-bold" className="mb-static-xs">{doc.title}</PText>
                          <PText size="small" className="text-contrast-medium line-clamp-4">
                            {doc.content}
                          </PText>
                        </div>
                        <PButtonPure icon="delete" className="text-error shrink-0" onClick={() => void deleteDocument(doc.id)} />
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="bg-surface border border-contrast-low rounded-lg overflow-hidden">
              <div className="px-fluid-md py-static-md border-b border-contrast-low flex items-center justify-between">
                <div>
                  <PHeading size="small">Select from Global Library</PHeading>
                  <PText size="small" className="text-contrast-medium">
                    Reuse previously uploaded sources without re-pasting content. You can select multiple sources at once.
                  </PText>
                </div>
                <div className="flex items-center gap-static-sm">
                  <PButton
                    loading={addingGlobalSources}
                    disabled={addingGlobalSources || selectedGlobalSourceIds.length === 0}
                    onClick={addSelectedFromGlobalLibrary}
                  >
                    {selectedGlobalSourceIds.length === 0 ? "Add Selected" : `Add Selected (${selectedGlobalSourceIds.length})`}
                  </PButton>
                  <PButton variant="secondary" icon="document" onClick={() => navigate("/sources")}>
                    Open Library
                  </PButton>
                </div>
              </div>

              <div className="p-fluid-md border-b border-contrast-low">
                <PText size="small" weight="semi-bold" className="mb-static-xs">Search Global Sources</PText>
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search by title, content, or type..."
                  className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary placeholder:text-contrast-low focus:outline-none focus:border-primary"
                  style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
                />
                <PText size="small" className="text-contrast-medium mt-static-xs">
                  {selectedVisibleCount > 0 ? `${selectedVisibleCount} selected in current results.` : "Select one or more sources, then click Add Selected."}
                </PText>
              </div>

              {filteredGlobalSources.length === 0 ? (
                <div className="p-fluid-lg flex flex-col items-center gap-static-md text-center">
                  <PIcon name="document" size="large" color="contrast-medium" />
                  <PText className="text-contrast-medium">
                    {globalSources.length === 0 ? "Global library is empty." : "No global sources match the current search."}
                  </PText>
                </div>
              ) : (
                <div className="divide-y divide-contrast-low">
                  {filteredGlobalSources.map((source) => {
                    const typeConfig = DOC_TYPES.find((type) => type.value === source.doc_type)!;
                    const alreadyLinked = linkedGlobalSourceIds.has(source.id);
                    const isSelected = selectedGlobalSourceIds.includes(source.id);
                    return (
                      <div key={source.id} className="p-fluid-sm flex gap-static-md items-start">
                        <div className="pt-static-xs w-4 shrink-0">
                          {!alreadyLinked && (
                            <input
                              type="checkbox"
                              checked={isSelected}
                              disabled={addingGlobalSources}
                              onChange={() => toggleGlobalSourceSelection(source.id)}
                              className="h-4 w-4 accent-[var(--p-color-state-success)] cursor-pointer disabled:cursor-not-allowed"
                            />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-static-sm mb-static-xs flex-wrap">
                            <PTag color={typeConfig.color}>{typeConfig.label}</PTag>
                            {alreadyLinked && <PTag color="notification-success-soft">Already in Case</PTag>}
                            {!alreadyLinked && isSelected && <PTag color="background-frosted">Selected</PTag>}
                            <PText size="small" className="text-contrast-low">
                              {new Date(source.created_at).toLocaleString()}
                            </PText>
                          </div>
                          <PText size="small" weight="semi-bold" className="mb-static-xs">{source.title}</PText>
                          <PText size="small" className="text-contrast-medium line-clamp-4">
                            {source.content}
                          </PText>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          <div className="col-span-2">
            <div className="bg-surface border border-contrast-low rounded-lg p-fluid-md sticky top-fluid-md">
              <PHeading size="small" className="mb-fluid-sm">Document Flow Guide</PHeading>
              <div className="flex flex-col gap-static-md mb-fluid-md">
                {DOC_TYPES.map((type) => (
                  <div key={type.value} className="flex gap-static-sm">
                    <PTag color={type.color}>{type.label}</PTag>
                    <PText size="small" className="text-contrast-medium">{type.desc}</PText>
                  </div>
                ))}
              </div>

              <PDivider className="mb-fluid-md" />

              <PText size="small" className="text-contrast-medium mb-fluid-sm">
                Case uploads become reusable global assets automatically. Selecting from the global library creates a case-local snapshot without altering the shared original.
              </PText>

              <PButton
                variant="primary"
                loading={extracting}
                disabled={extracting || documents.length === 0}
                icon="arrow-right"
                className="w-full"
                onClick={extractGraph}
              >
                {extracting
                  ? extractionStatus?.status === "pending"
                    ? "Queueing Extraction..."
                    : "Extracting Graph..."
                  : "Extract Knowledge Graph"}
              </PButton>

              {extractionStatus && (
                <PText size="small" className="text-contrast-medium mt-static-sm text-center">
                  {extractionStatus.status === "pending"
                    ? `Extraction queued for ${extractionStatus.document_count} documents.`
                    : extractionStatus.status === "running"
                      ? `Worker is processing ${extractionStatus.document_count} documents.`
                      : extractionStatus.status === "completed"
                        ? `Extraction completed with ${extractionStatus.entities_count} entities and ${extractionStatus.claims_count} claims.`
                        : "Extraction failed."}
                </PText>
              )}

              {documents.length < 3 && (
                <PText size="small" className="text-warning mt-static-sm text-center">
                  Recommended: add at least 3 documents
                </PText>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
