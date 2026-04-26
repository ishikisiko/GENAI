## 1. Baseline and Scope

- [x] 1.1 Run `npm run lint` and record the current React hook lint failures that must be fixed.
- [x] 1.2 Identify all affected frontend pages, including known pages and any additional pages surfaced by lint.
- [x] 1.3 Confirm the cleanup does not require backend, database, route, or API contract changes.

## 2. Normalize Effect-Driven Loading

- [x] 2.1 Refactor `DocumentsPage` initial data load so the effect uses an async runner with cancellation guard and does not call a synchronously stateful loader at effect entry.
- [x] 2.2 Refactor `GlobalSourcesPage` initial data load using the same pattern while preserving add/delete reload behavior.
- [x] 2.3 Refactor `SimulationPage` initial data load using the same pattern while preserving polling and run status refresh behavior.
- [x] 2.4 Refactor `SourceDiscoverySetupPage`, `CandidateSourcesReviewPage`, and `EvidencePackPreviewPage` to remove temporary lint-disable comments and use the normalized async effect pattern.
- [x] 2.5 Apply the same data-loading pattern to any additional page reported by the same lint rule.

## 3. Fix Derived State and Memoization

- [x] 3.1 Replace `SimulationPage` effect-based `injectionRound` synchronization with event-time clamping or a derived effective injection round.
- [x] 3.2 Remove unnecessary `useMemo` calls for cheap derived values that do not require stable identity.
- [x] 3.3 Rewrite retained memoized derived values, including `DocumentsPage` linked source ID sets, with explicit compiler-friendly logic.
- [x] 3.4 Remove broad or obsolete `eslint-disable` comments introduced only to bypass these hook lint issues.

## 4. Verification

- [x] 4.1 Run `npm run lint` and ensure it passes without project-wide React hook rule suppression.
- [x] 4.2 Run `npm run build` and ensure TypeScript and Vite still pass.
- [x] 4.3 Manually review changed pages to confirm user-triggered reloads, polling, and navigation flows remain equivalent.
- [x] 4.4 Record verification results and any unrelated residual warnings in the implementation summary.
