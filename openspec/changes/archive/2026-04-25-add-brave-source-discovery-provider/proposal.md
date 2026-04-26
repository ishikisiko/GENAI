## Why

Source discovery currently produces deterministic mock candidates, which is useful for local development but cannot ground a crisis case in real web evidence. The project now needs a production-capable Brave Search provider while preserving the existing mock fallback for environments without credentials.

## What Changes

- Add Brave Search as a real source discovery search provider.
- Configure provider selection through backend environment settings.
- Store Brave result metadata in candidate `provider_metadata` for auditability.
- Enforce the provided Brave API limit of one request per second.
- Keep mock discovery available as the default/fallback when Brave credentials are absent.
- Add a lightweight connectivity path or test coverage that proves the Brave provider can call the configured API without leaking the API key.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `source-discovery-evidence-packs`: Source discovery can use a configured real Brave Search provider instead of only the deterministic mock provider.

## Impact

- Backend configuration: new Brave Search provider settings and API key handling.
- Backend source discovery service: Brave Search provider implementation, rate limiting, response mapping, and fallback behavior.
- Worker runtime: uses configured source discovery provider when processing `source_discovery.run` jobs.
- Documentation/environment examples: document the required local environment variables without committing secrets.
- Tests: add focused coverage for Brave provider request construction, response parsing, and rate-limit behavior.
