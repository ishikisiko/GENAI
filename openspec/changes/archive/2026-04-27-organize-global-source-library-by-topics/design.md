## Context

CrisisSim currently has three source-related surfaces that are beginning to overlap: manually uploaded case documents, reusable `global_source_documents`, and discovery/evidence-pack records. The global library is stored as a flat table with document title, content, type, and creation time, while case-local `source_documents` are the stable grounding inputs used by graph extraction.

That flat model works for a small demo library but does not encode why a source belongs to a topic, whether it has already been used in a case, whether it is stale or duplicated, or which neighboring topics make it relevant. Source discovery also introduces topic-shaped work, but discovered candidates currently remain separate until evidence pack creation and grounding.

## Goals / Non-Goals

**Goals:**

- Add a topic/collection layer above global reusable sources.
- Allow a reusable source to belong to multiple topics with assignment rationale and provenance.
- Preserve case-local source snapshots when global sources are attached to a case.
- Provide smart views that keep unassigned, duplicate, stale, high-authority, and recently used sources discoverable without polluting main topic collections.
- Make case source selection topic-aware so users see case-relevant sources before the full global repository.
- Keep source discovery and evidence packs human-confirmed, with optional promotion into the source registry.
- Move source registry business operations behind the Python API instead of growing direct frontend writes to Supabase.

**Non-Goals:**

- Building a trained recommendation or credibility-ranking model.
- Automatically merging duplicate sources without user visibility.
- Replacing graph extraction inputs with a new document type.
- Automatically promoting every discovered candidate into the global library.
- Designing a final enterprise taxonomy for all topic types.

## Decisions

### Introduce topics and assignments instead of adding one topic column

Add `source_topics` and `source_topic_assignments` rather than a single topic field on `global_source_documents`. A source can legitimately belong to several crisis/product/stakeholder/regional collections, and assignments need their own relevance score, reason, and provenance.

Alternative considered: one `topic` or `tags` column on the global source row. That would be simpler but would make topic-specific relevance, assignment history, and multi-topic browsing hard to query and explain.

### Add case-topic links for case-relevant source selection

Add a lightweight case-to-topic association, such as `case_source_topics`, so the source selection page can distinguish "same topic", "related topic", and "global search" sources. This can be seeded from case creation, source discovery topics, or user selection.

Alternative considered: infer case relevance only from text search over case title and description. That is useful as a fallback, but it is too opaque for a durable source library and makes "why is this recommended?" difficult to explain.

### Keep global sources reusable and case documents immutable snapshots

Continue using `source_documents` as the grounding input. When a global source is added to a case, copy the current source fields and provenance metadata into a case-local source document. Later edits to the global source update future selections but do not mutate already attached case evidence.

Alternative considered: graph extraction reads directly from global sources. That would reduce duplication but would make grounding runs sensitive to later library edits and would blur reviewed case evidence with shared registry state.

### Extend global source metadata additively

Keep current `doc_type` compatibility while adding registry-oriented metadata such as `canonical_url`, `content_hash`, `source_kind`, `authority_level`, `freshness_status`, `source_status`, and `updated_at`. Existing rows backfill into Unassigned and can keep their current document type until migrated.

Alternative considered: replace `doc_type` with the discovery `source_type` vocabulary immediately. That risks breaking existing UI and seed data. The safer path is additive metadata plus a mapping layer.

### Treat smart views as queries, not folders

Smart views such as Unassigned, Recently Used, High Authority, Duplicate Candidates, and Stale Sources should be computed from source metadata, topic assignments, usage records, and dedupe fields. A source can appear in a topic and also in a smart view.

Alternative considered: create physical collections for every smart view. That would create synchronization problems and encourage users to move sources between system folders instead of assigning meaningful topic context.

### Promote discovery candidates only through explicit user action

Discovery candidates remain separate until the user confirms them. Accepted candidates can be saved to the global registry with a selected topic assignment or left Unassigned, but evidence pack creation and grounding continue to work even if the user does not save candidates globally.

Alternative considered: automatically write every discovered candidate to the global library. That would rapidly pollute the registry with unreviewed, low-quality, duplicate, or one-off search results.

## Risks / Trade-offs

- Topic taxonomy can become inconsistent -> Start with a small `topic_type` vocabulary and allow user-created names while keeping Unassigned visible for cleanup.
- More tables can make source selection slower -> Add indexes on topic assignment, canonical URL, content hash, source status, source kind, and source document usage; keep case selection endpoints server-side.
- Duplicate detection can create false positives -> Surface duplicate candidates through a smart view and status field, but do not auto-merge content.
- Existing direct Supabase frontend writes may bypass validation -> Route new source registry workflows through Python APIs and phase old direct writes toward compatibility-only usage.
- Topic recommendations may feel unexplained -> Store assignment reason, assigned_by, and case-topic relation reason so the UI can display why a source is recommended.
- Schema divergence between backend and Supabase migrations can reappear -> Add equivalent migrations in both paths and cover the contract with backend/API tests plus frontend boundary tests.

## Migration Plan

1. Add additive migrations for source topics, case-topic links, source-topic assignments, global source metadata, source document provenance fields, and supporting indexes.
2. Backfill existing global sources with `content_hash`, compatible `source_kind`, default status/freshness values, and no topic assignment so they appear in Unassigned.
3. Add backend repository/service contracts for topics, assignments, source registry listing, smart views, usage history, and case source selection.
4. Add Python API routes for source library and case source selection operations.
5. Update frontend types and API helpers.
6. Rework Global Source Library into topic-first navigation with smart views and source details.
7. Rework Case Documents source selection into recommended, same-topic, related, global search, and manual upload sections.
8. Add discovery candidate save-to-library behavior behind explicit user action.
9. Preserve existing manual upload, direct global selection, source discovery, evidence pack, and grounding flows during rollout.

Rollback is additive: hide the new UI routes/sections and continue reading existing `global_source_documents` and `source_documents`. The new topic and assignment tables can remain unused without affecting graph extraction.

## Open Questions

- What initial `topic_type` values should be exposed in the UI beyond crisis, product, region, stakeholder, and collection?
- Should users assign a case to topics during case creation, source discovery setup, or only when adding sources?
- Should authority and freshness be manually editable in the first version, derived from source type/provider metadata, or both?
- Should saving an accepted discovery candidate to the library happen from candidate review, evidence pack preview, or both?
