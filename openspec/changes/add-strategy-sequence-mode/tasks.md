## 1. Backend Contract And Persistence

- [x] 1.1 Add backend and Supabase migrations for nullable `simulation_runs.strategy_sequence`.
- [x] 1.2 Extend simulation domain records, request contracts, and job payloads with validated strategy sequence models.
- [x] 1.3 Persist strategy sequences when creating simulation submissions and include them in durable job payloads.

## 2. Simulation Execution

- [x] 2.1 Update worker simulation execution to apply per-round sequence strategies and preserve legacy single-injection behavior.
- [x] 2.2 Record applied strategies per round and provide bounded prior-strategy context in later sequence rounds.

## 3. Frontend Experience

- [x] 3.1 Extend frontend types and backend client payloads for strategy sequence submissions.
- [x] 3.2 Add SimulationPage controls for single-strategy versus sequence mode with per-round strategy/message editing.
- [x] 3.3 Update run and comparison labels so sequence runs are identifiable without breaking existing readers.

## 4. Verification

- [x] 4.1 Add or update backend tests for validation, persistence, and worker execution of strategy sequences.
- [x] 4.2 Run targeted backend and frontend checks for simulation contracts and UI build/lint coverage.
