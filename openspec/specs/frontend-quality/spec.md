# frontend-quality Specification

## Purpose
TBD - created by archiving change fix-react-hook-lint-patterns. Update Purpose after archive.
## Requirements
### Requirement: Frontend lint quality gate
The frontend SHALL pass the configured lint command without broad rule suppression after this cleanup.

#### Scenario: Full frontend lint is run
- **WHEN** a developer runs `npm run lint`
- **THEN** the command completes successfully
- **AND** the result does not depend on disabling React Hooks lint rules across whole files or the whole project

### Requirement: Effect-driven page loading follows React hook lint rules
Frontend pages SHALL avoid calling functions from `useEffect` that synchronously set React state at effect entry.

#### Scenario: Page performs initial async load
- **WHEN** a page starts an initial data load from `useEffect`
- **THEN** the effect starts an async operation without calling an external loader that immediately mutates component state
- **AND** state is committed only after awaited data is available and the effect has not been cancelled

#### Scenario: Component unmounts during async load
- **WHEN** a component unmounts or effect dependencies change before an async load resolves
- **THEN** the page does not update state from the stale load

### Requirement: User-triggered reload behavior is preserved
Frontend pages SHALL preserve existing user-triggered reload behavior while satisfying React hook lint rules.

#### Scenario: User action refreshes page data
- **WHEN** a user adds, deletes, submits, or refreshes data through an existing page action
- **THEN** the page can still reload the affected data
- **AND** the user-visible behavior remains equivalent to the pre-cleanup behavior

### Requirement: Compiler-friendly derived values
Frontend components SHALL avoid manual memoization patterns that React Compiler cannot preserve.

#### Scenario: Derived value is cheap to compute
- **WHEN** a derived value is inexpensive and does not require stable identity for child behavior
- **THEN** the component computes it directly instead of using `useMemo`

#### Scenario: Derived value still needs memoization
- **WHEN** a derived value benefits from memoization
- **THEN** the memoized calculation uses explicit, compiler-friendly logic
- **AND** it avoids unstable patterns such as broad `filter(Boolean)` type narrowing when those patterns trigger lint failures

### Requirement: Dependent state is not synchronized by lint-hostile effects
Frontend components SHALL avoid using effects only to keep one state variable inside the bounds of another state variable.

#### Scenario: Simulation total rounds changes
- **WHEN** the intervention total round count changes in `SimulationPage`
- **THEN** `injectionRound` remains valid through event-time clamping or a derived effective value
- **AND** the page does not rely on a `useEffect` whose only purpose is to synchronize that dependent state

### Requirement: Frontend build remains stable
The frontend SHALL continue to build successfully after React hook lint cleanup.

#### Scenario: Production frontend build is run
- **WHEN** a developer runs `npm run build`
- **THEN** TypeScript and Vite complete successfully
- **AND** no product route, API helper, or page flow is intentionally removed by the cleanup

