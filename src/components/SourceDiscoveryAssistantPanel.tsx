import { useState } from "react";
import {
  PButton, PHeading, PInlineNotification, PTag, PText,
} from "@porsche-design-system/components-react";
import { askSourceDiscoveryAssistant } from "../lib/backend";
import { getErrorMessage } from "../lib/errors";
import type {
  SourceDiscoveryAssistantCitation,
  SourceDiscoveryAssistantPlanningSuggestion,
  SourceDiscoveryAssistantRecommendedSettings,
  SourceDiscoveryAssistantRequest,
  SourceDiscoveryAssistantResponse,
} from "../lib/types";

interface SourceDiscoveryAssistantPanelProps {
  title: string;
  description: string;
  defaultQuestion: string;
  primaryActionLabel?: string;
  buildRequest: (question: string) => SourceDiscoveryAssistantRequest;
  briefingQuestion?: string;
  buildBriefingRequest?: (question: string) => SourceDiscoveryAssistantRequest;
  initialResponse?: SourceDiscoveryAssistantResponse | null;
  onResponse?: (response: SourceDiscoveryAssistantResponse) => void | Promise<void>;
  onApplySuggestion?: (
    suggestion: SourceDiscoveryAssistantPlanningSuggestion | SourceDiscoveryAssistantRecommendedSettings,
  ) => void;
}

function CitationList({ citations }: { citations: SourceDiscoveryAssistantCitation[] }) {
  if (!citations.length) return null;
  return (
    <div className="flex flex-col gap-static-xs">
      {citations.slice(0, 6).map((citation, index) => (
        <div key={`${citation.candidate_id || citation.title}-${index}`} className="bg-canvas rounded p-static-xs">
          <PText size="x-small" weight="semi-bold">
            {citation.candidate_id ? (
              <a href={`#candidate-${citation.candidate_id}`} className="underline underline-offset-2">
                {citation.title}
              </a>
            ) : citation.title}
          </PText>
          {citation.published_at && (
            <PText size="x-small" className="text-contrast-medium">{citation.published_at}</PText>
          )}
          {citation.quote && (
            <PText size="small" className="text-contrast-medium mt-static-xs">{citation.quote}</PText>
          )}
        </div>
      ))}
    </div>
  );
}

export default function SourceDiscoveryAssistantPanel({
  title,
  description,
  defaultQuestion,
  primaryActionLabel = "Ask Assistant",
  buildRequest,
  briefingQuestion,
  buildBriefingRequest,
  initialResponse,
  onResponse,
  onApplySuggestion,
}: SourceDiscoveryAssistantPanelProps) {
  const [question, setQuestion] = useState(defaultQuestion);
  const [response, setResponse] = useState<SourceDiscoveryAssistantResponse | null>(initialResponse ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(requestBuilder: (value: string) => SourceDiscoveryAssistantRequest = buildRequest) {
    setLoading(true);
    setError("");
    try {
      const nextResponse = await askSourceDiscoveryAssistant(requestBuilder(question.trim() || defaultQuestion));
      setResponse(nextResponse);
      await onResponse?.(nextResponse);
    } catch (error: unknown) {
      setError(getErrorMessage(error, "Assistant request failed."));
    }
    setLoading(false);
  }

  return (
    <div className="bg-surface border border-contrast-low rounded-lg p-fluid-md flex flex-col gap-fluid-sm">
      <div>
        <PHeading size="small">{title}</PHeading>
        <PText size="small" className="text-contrast-medium mt-static-xs">{description}</PText>
      </div>

      {error && (
        <PInlineNotification
          heading="Assistant unavailable"
          description={error}
          state="error"
          dismissButton
          onDismiss={() => setError("")}
        />
      )}

      <label className="flex flex-col gap-static-xs">
        <PText size="small" weight="semi-bold">Question</PText>
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          rows={3}
          className="w-full border border-contrast-low rounded bg-canvas px-static-sm py-static-xs text-primary focus:outline-none focus:border-primary resize-none"
          style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "14px" }}
        />
      </label>

      <div className="flex flex-col gap-static-xs sm:flex-row">
        <PButton icon="chat" loading={loading} disabled={loading} onClick={() => void submit(buildRequest)}>
          {primaryActionLabel}
        </PButton>
        {buildBriefingRequest && (
          <PButton
            variant="secondary"
            icon="search"
            loading={loading}
            disabled={loading}
            onClick={() => void submit((value) => {
              const briefingValue = value && value !== defaultQuestion ? value : briefingQuestion || defaultQuestion;
              return buildBriefingRequest(briefingValue);
            })}
          >
            Research Initial Timeline
          </PButton>
        )}
      </div>

      {response && (
        <div className="flex flex-col gap-static-sm border-t border-contrast-low pt-fluid-sm">
          {response.insufficient_evidence && (
            <PTag color="notification-warning-soft">Insufficient evidence</PTag>
          )}
          <PText size="small" className="text-contrast-medium">{response.answer}</PText>

          {response.briefing_limits && (
            <PText size="x-small" className="text-contrast-medium">
              Preliminary search: up to {response.briefing_limits.max_queries} queries,
              {" "}{response.briefing_limits.max_total_sources} sources.
            </PText>
          )}

          {(Boolean(response.key_actors.length) || Boolean(response.controversy_focus.length)) && (
            <div className="grid grid-cols-1 gap-static-xs sm:grid-cols-2">
              {Boolean(response.key_actors.length) && (
                <div className="bg-canvas rounded p-static-sm">
                  <PText size="small" weight="semi-bold">Key actors</PText>
                  <div className="flex flex-wrap gap-static-xs mt-static-xs">
                    {response.key_actors.slice(0, 8).map((actor) => (
                      <PTag key={actor} color="background-frosted">{actor}</PTag>
                    ))}
                  </div>
                </div>
              )}
              {Boolean(response.controversy_focus.length) && (
                <div className="bg-canvas rounded p-static-sm">
                  <PText size="small" weight="semi-bold">Controversy focus</PText>
                  <div className="flex flex-wrap gap-static-xs mt-static-xs">
                    {response.controversy_focus.slice(0, 8).map((focus) => (
                      <PTag key={focus} color="background-frosted">{focus}</PTag>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {response.recommended_settings && (
            <div className="bg-canvas rounded p-static-sm flex flex-col gap-static-xs">
              <PText size="small" weight="semi-bold">Recommended discovery settings</PText>
              {response.recommended_settings.topic && (
                <PText size="small" className="text-contrast-medium">{response.recommended_settings.topic}</PText>
              )}
              {Boolean(response.recommended_settings.source_types.length) && (
                <div className="flex flex-wrap gap-static-xs">
                  {response.recommended_settings.source_types.map((type) => (
                    <PTag key={type} color="background-frosted">{type}</PTag>
                  ))}
                </div>
              )}
              {onApplySuggestion && (
                <PButton variant="secondary" onClick={() => onApplySuggestion(response.recommended_settings!)}>
                  Apply recommended settings
                </PButton>
              )}
            </div>
          )}

          {Boolean(response.source_summaries.length) && (
            <div className="flex flex-col gap-static-xs">
              <PText size="small" weight="semi-bold">Searched sources</PText>
              {response.source_summaries.slice(0, 6).map((source, index) => (
                <div key={`${source.url || source.title}-${index}`} className="bg-canvas rounded p-static-sm">
                  <div className="flex flex-wrap gap-static-xs mb-static-xs">
                    <PTag color="background-frosted">{source.source_type}</PTag>
                    {source.published_at && <PTag color="notification-info-soft">{source.published_at}</PTag>}
                  </div>
                  <PText size="small" weight="semi-bold">{source.title}</PText>
                  {source.url && <PText size="x-small" className="text-contrast-low truncate">{source.url}</PText>}
                  <PText size="small" className="text-contrast-medium mt-static-xs">{source.summary}</PText>
                  {source.citation && (
                    <div className="mt-static-xs">
                      <CitationList citations={[source.citation]} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {Boolean(response.planning_suggestions.length) && (
            <div className="flex flex-col gap-static-xs">
              <PText size="small" weight="semi-bold">Search directions</PText>
              {response.planning_suggestions.map((suggestion) => (
                <div key={suggestion.label} className="bg-canvas rounded p-static-sm flex flex-col gap-static-xs">
                  <PText size="small" weight="semi-bold">{suggestion.label}</PText>
                  {suggestion.rationale && (
                    <PText size="small" className="text-contrast-medium">{suggestion.rationale}</PText>
                  )}
                  {Boolean(suggestion.queries.length) && (
                    <div className="flex flex-wrap gap-static-xs">
                      {suggestion.queries.slice(0, 4).map((query) => (
                        <PTag key={query} color="background-frosted">{query}</PTag>
                      ))}
                    </div>
                  )}
                  {onApplySuggestion && (
                    <PButton variant="secondary" onClick={() => onApplySuggestion(suggestion)}>
                      Apply to form
                    </PButton>
                  )}
                </div>
              ))}
            </div>
          )}

          {Boolean(response.timeline.length) && (
            <div className="flex flex-col gap-static-xs">
              <PText size="small" weight="semi-bold">Timeline</PText>
              {response.timeline.map((item, index) => (
                <div key={`${item.title}-${index}`} className="bg-canvas rounded p-static-sm">
                  <div className="flex flex-wrap gap-static-xs mb-static-xs">
                    {item.event_date && <PTag color="notification-info-soft">Event: {item.event_date}</PTag>}
                    {item.reporting_date && <PTag color="background-frosted">Reported: {item.reporting_date}</PTag>}
                  </div>
                  <PText size="small" weight="semi-bold">{item.title}</PText>
                  <PText size="small" className="text-contrast-medium mt-static-xs">{item.summary}</PText>
                  <div className="mt-static-xs">
                    <CitationList citations={item.citations} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {Boolean(response.event_stages.length) && (
            <div className="flex flex-col gap-static-xs">
              <PText size="small" weight="semi-bold">Event stages</PText>
              {response.event_stages.map((stage) => (
                <div key={stage.name} className="bg-canvas rounded p-static-sm">
                  <div className="flex flex-wrap gap-static-xs mb-static-xs">
                    <PTag color="notification-info-soft">{stage.confidence}</PTag>
                  </div>
                  <PText size="small" weight="semi-bold">{stage.name}</PText>
                  <PText size="small" className="text-contrast-medium mt-static-xs">{stage.summary}</PText>
                  <div className="mt-static-xs">
                    <CitationList citations={stage.citations} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {Boolean(response.conflicts.length) && (
            <div className="flex flex-col gap-static-xs">
              <PText size="small" weight="semi-bold">Conflicts</PText>
              {response.conflicts.map((conflict, index) => (
                <div key={`${conflict.summary}-${index}`} className="bg-canvas rounded p-static-sm">
                  <PText size="small" className="text-contrast-medium">{conflict.summary}</PText>
                  <div className="flex flex-wrap gap-static-xs mt-static-xs">
                    {conflict.sides.map((side) => <PTag key={side} color="background-frosted">{side}</PTag>)}
                  </div>
                  <div className="mt-static-xs">
                    <CitationList citations={conflict.citations} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {Boolean(response.evidence_gaps.length || response.follow_up_searches.length) && (
            <div className="flex flex-col gap-static-xs">
              <PText size="small" weight="semi-bold">Follow-up searches</PText>
              {response.evidence_gaps.map((gap, index) => (
                <PText key={`${gap.summary}-${index}`} size="small" className="text-contrast-medium">
                  {gap.summary}
                </PText>
              ))}
              <div className="flex flex-wrap gap-static-xs">
                {[...response.follow_up_searches, ...response.evidence_gaps.flatMap((gap) => gap.follow_up_searches)]
                  .slice(0, 8)
                  .map((query) => <PTag key={query} color="background-frosted">{query}</PTag>)}
              </div>
            </div>
          )}

          <CitationList citations={response.citations} />
        </div>
      )}
    </div>
  );
}
