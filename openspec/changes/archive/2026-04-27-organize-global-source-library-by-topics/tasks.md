## 1. Data Model and Migrations

- [x] 1.1 Add backend and Supabase migrations for `source_topics`, `case_source_topics`, and `source_topic_assignments` with foreign keys, uniqueness constraints, status fields, and timestamps.
- [x] 1.2 Extend `global_source_documents` with canonical URL, content hash, source kind, authority level, freshness status, source status, and `updated_at` metadata while preserving existing `doc_type` compatibility.
- [x] 1.3 Extend `source_documents` provenance metadata so case-local snapshots can record selected topic, assignment, registry metadata, and source origin details.
- [x] 1.4 Add indexes for topic hierarchy, topic assignments, case-topic links, canonical URL, content hash, source status, source kind, and case source usage queries.
- [x] 1.5 Backfill existing global sources with content hashes, compatible source kind values, default authority/freshness/status values, and no topic assignments so they appear in Unassigned.
- [x] 1.6 Update seed/demo data to include representative topics, topic assignments, unassigned sources, duplicates, and case-topic links.

## 2. Backend Domain, Repository, and Services

- [x] 2.1 Add domain records and service contract models for source topics, case-topic links, topic assignments, source registry results, smart views, usage summaries, and case source selection groups.
- [x] 2.2 Implement repository methods to create, list, update, and fetch source topics including parent-child relationships.
- [x] 2.3 Implement repository methods to assign and remove global sources from topics with relevance, reason, and assignment provenance.
- [x] 2.4 Implement global source create/update helpers that compute content hashes, normalize canonical URLs, preserve compatibility fields, and detect duplicate candidates without auto-merging.
- [x] 2.5 Implement smart view queries for Unassigned, Recently Used, High Authority, Duplicate Candidates, and Stale Sources.
- [x] 2.6 Implement source usage queries derived from case-local `source_documents` and topic assignment records.
- [x] 2.7 Implement case source selection service logic for Recommended for this case, Same topic collections, Related collections, Global search, and already-in-case markers.
- [x] 2.8 Implement attach-from-library logic that creates immutable case-local source document snapshots and rejects duplicate source attachments for the same case.

## 3. Python API Boundary

- [x] 3.1 Add Python API routes for creating, updating, listing, and fetching source topics.
- [x] 3.2 Add Python API routes for creating and deleting source-topic assignments.
- [x] 3.3 Add Python API routes for querying source registry results by topic, smart view, metadata filters, and text search.
- [x] 3.4 Add Python API routes for source usage details.
- [x] 3.5 Add Python API routes for case source selection and attach-from-library snapshot creation.
- [x] 3.6 Ensure API errors use the shared backend error envelope for invalid topics, missing sources, duplicate case attachments, and invalid smart view names.
- [x] 3.7 Add backend API tests covering topic management, assignment updates, smart views, case selection grouping, source usage, and duplicate attach rejection.

## 4. Source Discovery Integration

- [x] 4.1 Add service logic to save an accepted discovery candidate into the source registry only when the user explicitly requests it.
- [x] 4.2 Support saving an accepted candidate to a selected topic by creating or reusing a global source and creating a source-topic assignment with discovery provenance metadata.
- [x] 4.3 Support saving an accepted candidate as Unassigned by creating or reusing the global source without a topic assignment.
- [x] 4.4 Keep evidence pack creation available for accepted candidates that are not saved to the source registry.
- [x] 4.5 Prevent rejected candidates from being automatically promoted into the source registry.
- [x] 4.6 Add tests for candidate save-to-topic, candidate save-as-unassigned, dedupe reuse, and no-auto-promotion behavior.

## 5. Frontend Source Registry Experience

- [x] 5.1 Update frontend types and backend API helpers for topics, assignments, source registry results, smart views, source usage, and case source selection.
- [x] 5.2 Rework `GlobalSourcesPage` into a topic-first source registry with topic navigation, smart view navigation, source list, and source details.
- [x] 5.3 Add source filtering controls for source kind, authority level, freshness status, source status, and text query.
- [x] 5.4 Add UI controls to assign a source to a topic, remove a source from a topic, and view assignment reasons/provenance.
- [x] 5.5 Add source usage visibility showing topic assignments and crisis case usage records.
- [x] 5.6 Ensure Unassigned, Duplicate Candidates, and Stale Sources are visible maintenance views rather than hidden filter states.

## 6. Frontend Case Source Selection

- [x] 6.1 Rework the case document source selection surface into Recommended for this case, Same topic collections, Related collections, Global search, and Manual upload sections.
- [x] 6.2 Mark sources already attached to the current case and prevent selecting them again.
- [x] 6.3 Route add-from-library actions through the Python API snapshot endpoint instead of direct Supabase insertion.
- [x] 6.4 Preserve manual upload behavior and ensure uploaded case documents still sync to reusable global sources where existing behavior requires it.
- [x] 6.5 Add explicit case-topic association UI or fallback behavior so users can understand why recommended sources appear.
- [x] 6.6 Add frontend tests or boundary coverage for grouped selection, already-in-case markers, and add-from-library API usage.

## 7. Verification and Compatibility

- [x] 7.1 Verify existing manual upload, global library selection, source discovery, evidence pack preview, and evidence pack grounding flows still work.
- [x] 7.2 Run backend tests covering source registry, source discovery integration, and existing API flows.
- [x] 7.3 Run frontend lint/build checks after the UI and type changes.
- [x] 7.4 Run or update OpenSpec validation for the new `source-library-topics` capability and modified capability deltas.
- [x] 7.5 Document any remaining taxonomy or recommendation open questions for follow-up after implementation.
