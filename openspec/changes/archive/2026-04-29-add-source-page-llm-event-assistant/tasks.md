## 1. Backend Contracts

- [x] 1.1 Add source discovery assistant request and response models for `search_planning` and `source_interpretation` modes.
- [x] 1.2 Define structured response fields for answer text, planning suggestions, timeline items, event stages, citations, conflicts, evidence gaps, and follow-up search directions.
- [x] 1.3 Add validation for required mode-specific context, including case context for search planning and discovery job identity for source interpretation.

## 2. Backend Service and API

- [x] 2.1 Implement a source discovery assistant service that builds bounded prompts from case, discovery form, discovery job, and candidate source context.
- [x] 2.2 Reuse the existing LLM client configuration and return stable product errors when LLM configuration or requests fail.
- [x] 2.3 Add a Python API endpoint for source discovery assistant requests that does not expose LLM provider calls to the frontend.
- [x] 2.4 Ensure source interpretation mode loads only candidates for the requested discovery job and returns insufficient-evidence responses when grounding context is missing or inadequate.

## 3. Frontend Integration

- [x] 3.1 Add backend client helpers and TypeScript types for source discovery assistant requests and responses.
- [x] 3.2 Create a shared assistant UI component that can render loading, errors, answer text, citations, planning suggestions, timeline items, conflicts, evidence gaps, and follow-up searches.
- [x] 3.3 Integrate the assistant into `SourceDiscoverySetupPage` in search planning mode and allow explicit user action to apply supported suggestions to discovery form fields.
- [x] 3.4 Integrate the assistant into `CandidateSourcesReviewPage` in source interpretation mode and link citations back to visible candidate source identifiers or titles.
- [x] 3.5 Keep candidate review, evidence pack creation, grounding, and simulation actions separate from assistant output.

## 4. Tests and Verification

- [x] 4.1 Add backend tests for request validation, mode-specific grounding, structured response mapping, insufficient-evidence behavior, and LLM error handling.
- [x] 4.2 Add frontend tests or focused component coverage for assistant rendering states and explicit apply-to-form behavior.
- [x] 4.3 Verify source discovery setup still creates jobs only through the existing explicit submit action.
- [x] 4.4 Verify candidate review assistant output cannot change candidate review status or create evidence packs without existing user actions.
- [x] 4.5 Run the relevant backend and frontend test suites and record any environment limitations.
