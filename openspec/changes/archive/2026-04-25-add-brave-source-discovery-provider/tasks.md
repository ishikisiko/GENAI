## 1. Configuration

- [x] 1.1 Add backend settings for source discovery provider, Brave API key, Brave endpoint, result count, country, language, and one-request-per-second interval.
- [x] 1.2 Document local Brave environment variables without committing the secret key.

## 2. Provider Implementation

- [x] 2.1 Implement a Brave Search provider that calls the web search endpoint with `X-Subscription-Token`.
- [x] 2.2 Map Brave web results into existing `SearchResult` values with provider metadata preserved.
- [x] 2.3 Enforce provider-level one request per second throttling.
- [x] 2.4 Wire API and worker service construction to select Brave or mock from config.

## 3. Verification

- [x] 3.1 Add focused tests for Brave request headers, query parameters, response mapping, and throttling behavior.
- [x] 3.2 Run a single live Brave connectivity check using the local API key and confirm at least one result maps successfully.
