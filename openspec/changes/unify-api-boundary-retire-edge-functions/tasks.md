## 1. Shared backend contract

- [ ] 1.1 Add a shared Python API request-context/auth layer that applies product-endpoint auth rules, request correlation, and the unified product error envelope.
- [ ] 1.2 Define one consistent synchronous response contract and one consistent async submission/status contract, then expose them through shared backend schemas/helpers.
- [ ] 1.3 Introduce or consolidate frontend backend-client helpers so product pages stop building Python API and Edge Function requests independently.

## 2. Agent generation migration

- [ ] 2.1 Implement a Python-owned agent-generation service and API endpoint that preserves the current persistence semantics for `agent_profiles` and case status updates.
- [ ] 2.2 Update the grounding flow to call the Python API agent-generation endpoint and keep the current success path into simulation.
- [ ] 2.3 Add backend endpoint/service tests for successful agent generation, handled failures, and no-partial-success behavior.

## 3. Async workflow alignment

- [ ] 3.1 Align simulation submission and polling responses with the shared async contract without changing simulation business semantics.
- [ ] 3.2 Align graph-extraction submission and polling responses with the shared async contract without changing extraction pipeline semantics.
- [ ] 3.3 Update frontend callers for simulation and graph extraction to use the shared backend client and the canonical async status surfaces.

## 4. Compatibility-layer convergence

- [ ] 4.1 Decide which legacy Edge Functions remain temporarily for rollback and mark each retained function as compatibility-only in code and docs.
- [ ] 4.2 Remove or forward the old `generate-agents` Edge Function path once the Python API cutover is in place.
- [ ] 4.3 Remove stale frontend config branches, headers, or env assumptions that still treat Edge Functions as primary product endpoints.

## 5. Observability and cleanup

- [ ] 5.1 Ensure product API failures and async job flows emit correlated structured logs that operators can trace with request IDs and job IDs.
- [ ] 5.2 Update `README.md`, `backend/README.md`, and rollout notes so Python API + worker is the default local and rollout story, with compatibility layers documented only where still retained.
- [ ] 5.3 Prune obsolete local development scripts or instructions that existed only for the old mixed Edge Function business path.
