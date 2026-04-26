## Context

The Vite/React frontend uses the recommended React Hooks lint configuration, including React Compiler-oriented rules. Full `npm run lint` currently fails because several pages use the same pattern: an effect calls a memoized loader, and that loader immediately calls `setLoading(true)` or other state setters before awaiting external data. `DocumentsPage` also contains manual memoization that the compiler cannot preserve.

This is a cross-page cleanup rather than a feature change. The implementation should keep current routes, API calls, Supabase queries, polling behavior, and UI output stable while making the code conform to the configured lint rules.

## Goals / Non-Goals

**Goals:**
- Make `npm run lint` pass for the frontend.
- Keep `npm run build` passing.
- Normalize effect-driven page data loading across affected pages.
- Preserve user-triggered reloads after add, delete, submit, polling, and navigation workflows.
- Remove or rewrite compiler-hostile manual memoization.
- Avoid broad `eslint-disable` comments.

**Non-Goals:**
- Introduce a new data-fetching or state-management library.
- Redesign frontend routing, visual layout, or business workflows.
- Move existing Supabase reads to the Python backend.
- Change backend code, database schema, or OpenSpec source-discovery behavior.
- Add large UI test infrastructure where build and lint verification are sufficient.

## Decisions

### Use local async effect runners instead of effect-called loaders

For initial page loads, each affected component will define an async function inside the `useEffect` body or call a helper that does not synchronously set React state. The effect runner will await data, check a cancellation flag, and then commit page state.

Alternative considered: keep the existing `load()` callbacks and silence lint. That would preserve the current code shape but leaves the project dependent on exceptions to the configured quality gate.

### Keep user-action reload helpers separate

Pages can still expose reload functions for event handlers such as add/delete/refresh. These helpers may set loading or status state because they are called from user events or async callbacks, not directly from effect entry. Where shared fetch logic is useful, split it into a pure async `fetch...` helper that returns data and a stateful event reload wrapper that applies state.

Alternative considered: move all loading into a shared hook immediately. A hook may be useful later, but this cleanup should stay small and avoid an abstraction that must fit every page's different result shape.

### Prefer ordinary derived values for cheap computations

For small lists and straightforward derived values, remove `useMemo` and compute directly during render. For heavier or identity-sensitive derived values, keep `useMemo` but use explicit loops and type guards that React Compiler can preserve.

Alternative considered: keep all current `useMemo` calls and add exceptions. That misses the chance to simplify code and may continue to trigger compiler warnings.

### Clamp dependent state at the event boundary

`SimulationPage` should not use an effect solely to adjust `injectionRound` after `interventionTotalRounds` changes. The total-rounds update handler should clamp `injectionRound`, or submission/rendering should use a derived effective injection round.

Alternative considered: leave effect-based synchronization and disable the lint rule for that line. This is a narrow issue with a straightforward state-model fix.

## Risks / Trade-offs

- Initial loading indicators could behave differently if `setLoading(true)` is removed from initial effects -> Keep initial `loading` state as `true` and only change to `false` after the first async load completes.
- Event-driven refresh behavior could regress when splitting fetch and state application -> Preserve existing reload wrappers and verify add/delete/polling flows still call them.
- Cancellation guards add repeated boilerplate -> Prefer local consistency over premature abstraction; extract a hook only if repeated shape becomes obvious during implementation.
- Removing `useMemo` could recompute derived values more often -> Only remove memoization for cheap list operations; retain compiler-friendly memoization where cost or identity matters.
- Source-discovery pages currently include temporary lint comments from the prior change -> Replace those with the same normalized effect pattern rather than leaving special cases.

## Migration Plan

1. Run `npm run lint` or use the previous lint output to identify current frontend failures.
2. Refactor affected page loaders using the normalized async effect runner pattern.
3. Refactor compiler-hostile memoization and `SimulationPage` dependent state synchronization.
4. Remove temporary local lint-disable comments that are no longer necessary.
5. Run `npm run lint` and `npm run build`.

Rollback is simple: revert the frontend cleanup files. No persisted data or API contract is affected.

## Open Questions

- If additional React Compiler warnings appear after the initial fixes, should they be folded into this cleanup or handled as a follow-up? Default: include same-rule findings in this cleanup, defer unrelated style or performance refactors.
