import { useCallback, useEffect, useMemo, useState } from "react";
import {
  PButton, PButtonPure, PHeading, PIcon, PInlineNotification, PSpinner, PTag, PText,
} from "@porsche-design-system/components-react";
import PageHeader from "../components/PageHeader";
import { supabase } from "../lib/supabase";
import type { DocType, GlobalSourceDocument } from "../lib/types";
import { DOC_TYPE_LABELS } from "../lib/constants";

const DOC_TYPES: { value: DocType; label: string; desc: string; color: "notification-info-soft" | "notification-warning-soft" | "notification-success-soft" }[] = [
  { value: "news", label: "News Report", desc: "Media coverage or journalism", color: "notification-info-soft" },
  { value: "complaint", label: "User Complaint", desc: "Consumer feedback or complaint", color: "notification-warning-soft" },
  { value: "statement", label: "Official Statement", desc: "Corporate or government statement", color: "notification-success-soft" },
];

export default function GlobalSourcesPage() {
  const [sources, setSources] = useState<GlobalSourceDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [query, setQuery] = useState("");

  const [docTitle, setDocTitle] = useState("");
  const [docContent, setDocContent] = useState("");
  const [docType, setDocType] = useState<DocType>("news");

  const loadSources = useCallback(async () => {
    setLoading(true);
    const { data, error: loadError } = await supabase
      .from("global_source_documents")
      .select("*")
      .order("created_at", { ascending: false });

    if (loadError) {
      setError(loadError.message);
    } else {
      setSources(data ?? []);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void loadSources();
  }, [loadSources]);

  async function addGlobalSource() {
    if (!docContent.trim()) {
      setError("Document content is required.");
      return;
    }

    setAdding(true);
    setError("");
    setSuccess("");

    const { error: insertError } = await supabase.from("global_source_documents").insert({
      title: docTitle.trim() || `${DOC_TYPE_LABELS[docType]} ${sources.length + 1}`,
      content: docContent.trim(),
      doc_type: docType,
    });

    if (insertError) {
      setError(insertError.message);
      setAdding(false);
      return;
    }

    setDocTitle("");
    setDocContent("");
    setDocType("news");
    setShowForm(false);
    setSuccess("Source added to the global repository.");
    setAdding(false);
    await loadSources();
  }

  async function deleteGlobalSource(id: string) {
    setError("");
    setSuccess("");
    const { error: deleteError } = await supabase.from("global_source_documents").delete().eq("id", id);

    if (deleteError) {
      setError(deleteError.message);
      return;
    }

    setSources((current) => current.filter((doc) => doc.id !== id));
    setSuccess("Global source deleted.");
  }

  const filteredSources = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return sources;
    return sources.filter((source) =>
      source.title.toLowerCase().includes(normalized)
      || source.content.toLowerCase().includes(normalized)
      || DOC_TYPE_LABELS[source.doc_type].toLowerCase().includes(normalized)
    );
  }, [query, sources]);

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
        title="Global Source Library"
        subtitle="Manage reusable source material that can be attached to any crisis case."
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Source Library" }]}
        action={(
          <PButton icon="add" onClick={() => setShowForm((current) => !current)}>
            Add Global Source
          </PButton>
        )}
      />

      <div className="p-fluid-lg max-w-5xl flex flex-col gap-fluid-md">
        {error && (
          <PInlineNotification
            heading="Error"
            description={error}
            state="error"
            dismissButton
            onDismiss={() => setError("")}
          />
        )}
        {success && (
          <PInlineNotification
            heading="Success"
            description={success}
            state="success"
            dismissButton
            onDismiss={() => setSuccess("")}
          />
        )}

        <div className="bg-surface border border-contrast-low rounded-lg p-fluid-md">
          <PText size="small" weight="semi-bold" className="mb-static-xs">Search Library</PText>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by title, content, or type..."
            className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary placeholder:text-contrast-low focus:outline-none focus:border-primary"
            style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "15px" }}
          />
        </div>

        {showForm && (
          <div className="bg-surface border border-contrast-low rounded-lg p-fluid-md flex flex-col gap-fluid-sm">
            <PHeading size="small">New Global Source</PHeading>

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
              <PButton loading={adding} disabled={adding || !docContent.trim()} onClick={addGlobalSource}>
                Save to Library
              </PButton>
              <PButton variant="secondary" onClick={() => setShowForm(false)}>
                Cancel
              </PButton>
            </div>
          </div>
        )}

        <div className="bg-surface border border-contrast-low rounded-lg overflow-hidden">
          <div className="px-fluid-md py-static-md border-b border-contrast-low flex items-center justify-between">
            <PHeading size="small">Repository Documents</PHeading>
            <PText size="small" className="text-contrast-medium">{filteredSources.length} items</PText>
          </div>

          {filteredSources.length === 0 ? (
            <div className="p-fluid-lg flex flex-col items-center gap-static-sm text-center">
              <PIcon name="document" size="large" color="contrast-medium" />
              <PText className="text-contrast-medium">
                {sources.length === 0 ? "No global sources yet." : "No sources match the current search."}
              </PText>
            </div>
          ) : (
            <div className="divide-y divide-contrast-low">
              {filteredSources.map((source) => {
                const typeConfig = DOC_TYPES.find((type) => type.value === source.doc_type)!;
                return (
                  <div key={source.id} className="p-fluid-sm flex gap-static-md">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-static-sm mb-static-xs">
                        <PTag color={typeConfig.color}>{typeConfig.label}</PTag>
                        <PText size="small" className="text-contrast-low">
                          {new Date(source.created_at).toLocaleString()}
                        </PText>
                      </div>
                      <PText size="small" weight="semi-bold" className="mb-static-xs">{source.title}</PText>
                      <PText size="small" className="text-contrast-medium whitespace-pre-line">
                        {source.content}
                      </PText>
                    </div>
                    <PButtonPure icon="delete" className="text-error shrink-0" onClick={() => void deleteGlobalSource(source.id)} />
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
