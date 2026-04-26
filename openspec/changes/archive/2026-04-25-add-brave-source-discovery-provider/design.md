## Context

Source discovery already has a provider boundary: `SearchProvider.search()` returns normalized `SearchResult` objects, and the worker pipeline handles query expansion, fetch, dedupe, classification, scoring, preview extraction, and candidate persistence. The current default provider is deterministic mock search.

The Brave Search API uses the web search endpoint with the API key passed in the `X-Subscription-Token` header. The supplied subscription has a one request per second limit, so the backend must serialize Brave calls inside the provider rather than relying on callers to pace requests.

## Goals / Non-Goals

**Goals:**

- Add a Brave Search provider behind the existing `SearchProvider` interface.
- Select `mock` or `brave` through backend configuration.
- Keep secrets out of committed files and API responses.
- Preserve the existing mock provider for local development and missing credentials.
- Enforce one Brave request per second per backend worker process.
- Map Brave web results into the existing candidate schema without changing database tables.

**Non-Goals:**

- Add multi-provider fanout or SERP fallback orchestration.
- Fetch and parse full article bodies from target URLs.
- Add a frontend provider selector.
- Change the human review or evidence pack workflow.

## Decisions

- Use `SOURCE_DISCOVERY_SEARCH_PROVIDER` with values `mock` and `brave`.
  - Rationale: explicit backend configuration keeps frontend behavior stable and matches existing environment-driven backend config.
  - Alternative considered: auto-enable Brave whenever a key exists. Rejected because it makes local behavior less predictable.

- Store the Brave API key in `BRAVE_SEARCH_API_KEY`.
  - Rationale: follows Brave documentation naming conventions and keeps the key in runtime environment only.
  - Alternative considered: store the key in source discovery job payload. Rejected because payloads are persisted.

- Implement rate limiting in the provider with a process-local async lock and monotonic clock.
  - Rationale: source discovery can expand to multiple queries per job, and the provider is the narrowest place that can enforce the external API contract.
  - Alternative considered: add sleeps in the worker loop. Rejected because it would spread provider-specific behavior outside the provider boundary.

- Map Brave `web.results` items to `SearchResult`.
  - Rationale: the existing pipeline already owns classification, scoring, and persistence.
  - Alternative considered: persist raw Brave payloads directly as candidates. Rejected because it would bypass existing normalization and make downstream logic provider-specific.

## Risks / Trade-offs

- [Risk] Process-local throttling does not coordinate across multiple worker processes. → Mitigation: document that one free-tier key should be used with one active source-discovery worker or a higher Brave plan; future distributed rate limiting can be added if needed.
- [Risk] Brave result snippets are not full page content. → Mitigation: use the existing content fetcher abstraction for now and preserve Brave metadata for later full-content fetch work.
- [Risk] A missing or invalid key could break discovery jobs. → Mitigation: fail fast on invalid Brave configuration and keep `mock` as the local default.
- [Risk] Live connectivity tests consume quota. → Mitigation: keep automated tests mocked and run one explicit manual live call when requested.
