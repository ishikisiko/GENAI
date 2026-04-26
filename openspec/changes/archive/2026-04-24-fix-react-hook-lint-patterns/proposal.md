## Why

The frontend currently fails full `npm run lint` because several page-level React data-loading patterns conflict with the configured React Hooks and React Compiler lint rules. Cleaning these patterns up now restores a reliable frontend quality gate without changing product behavior.

## What Changes

- Normalize page data-loading effects so they do not call external functions that synchronously set state at effect entry.
- Add cancellation guards around async effect-driven loads to avoid setting state after unmount or dependency changes.
- Preserve explicit reload behavior for user actions such as add, delete, refresh, polling, and post-submit navigation.
- Remove unnecessary manual memoization for simple derived values, or rewrite retained memoization in compiler-friendly forms.
- Replace `SimulationPage` effect-driven state synchronization for `injectionRound` with event-time clamping or a derived effective value.
- Avoid broad `eslint-disable` usage; only retain narrow comments where a rule exception is intentional and justified.
- Verify the cleanup with `npm run lint` and `npm run build`.

## Capabilities

### New Capabilities
- `frontend-quality`: Covers frontend lint/build quality gates, React hook data-loading conventions, compiler-friendly memoization, and behavior-preserving cleanup expectations.

### Modified Capabilities
- None.

## Impact

- Frontend pages: `DocumentsPage`, `GlobalSourcesPage`, `SimulationPage`, `SourceDiscoverySetupPage`, `CandidateSourcesReviewPage`, `EvidencePackPreviewPage`, and any additional pages flagged by the same lint rules.
- Frontend quality tooling: `npm run lint` becomes a required passing verification for this cleanup.
- No backend API, database schema, route, or user-facing workflow changes are intended.
