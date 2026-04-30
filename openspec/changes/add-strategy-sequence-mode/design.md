## Context

Simulation interventions are currently modeled as one strategy injected at one round. The frontend submits `strategy_type`, optional `strategy_message`, and `injection_round`; the backend stores those fields on `simulation_runs` and passes them through the durable job payload. During worker execution, only the injection round receives the public response and later rounds receive an ongoing-effect note.

The new sequence mode should remain a planned fixed-run workflow, not a human-in-the-loop step simulator. Users configure the whole intervention plan before submission, the existing worker runs all rounds asynchronously, and downstream pages continue reading `simulation_runs`, `round_states`, and `metric_snapshots`.

## Goals / Non-Goals

**Goals:**

- Allow intervention submissions to include an ordered per-round strategy plan.
- Preserve existing single-strategy intervention behavior and baseline behavior.
- Persist enough run-level data to label and inspect sequence runs after completion.
- Keep round result storage compatible by recording the strategy applied on each round through existing `round_states.strategy_applied`.
- Keep the API and worker validation deterministic so invalid plans fail before jobs are created.

**Non-Goals:**

- No pause/resume human-in-the-loop execution between rounds.
- No automatic strategy selection by the LLM or optimization engine.
- No new strategy taxonomy beyond the existing strategy types.
- No rewrite of comparison scoring or simulation metrics.

## Decisions

1. Store the planned sequence on `simulation_runs.strategy_sequence` as JSONB and copy it into the durable job payload.

   Rationale: the sequence is run-level configuration and must remain visible after job completion. JSONB keeps the migration small and avoids introducing a child table before the model needs querying by individual planned step.

   Alternative considered: create a `simulation_strategy_steps` table. That would support richer future querying, but it adds joins and repository complexity for a small bounded list of up to 20 rounds.

2. Represent each step as `{ round_number, strategy_type, strategy_message? }`.

   Rationale: explicit round numbers make the payload robust if UI arrays are reordered or omit no-op rounds. The backend can validate bounds, duplicates, and strategy values before creating a run.

   Alternative considered: array index equals round number. That is compact but more fragile and harder to validate clearly.

3. Treat sequence mode as mutually exclusive with single-strategy mode at submission time.

   Rationale: a run should have one unambiguous intervention model. Existing fields remain supported for compatibility; new sequence submissions include `strategy_sequence` and do not require `injection_round`.

   Alternative considered: merge `strategy_sequence` with a legacy injected strategy. That creates ambiguous precedence rules and makes comparison labels harder to explain.

4. Apply one configured strategy per round, with no-op rounds allowed.

   Rationale: users need to model planned pauses. The worker should apply strategy context only when the current round has a sequence step. Later rounds should refer to prior issued strategies as ongoing context.

   Alternative considered: require every round to have a strategy. That over-constrains realistic crisis response plans and forces meaningless actions.

## Risks / Trade-offs

- [Risk] JSONB sequence data can drift from TypeScript/Pydantic contracts if shapes are changed casually. -> Mitigation: validate through backend Pydantic models and add contract tests.
- [Risk] Comparison labels may become noisy for long sequences. -> Mitigation: label sequence runs by count and first applied strategy, while detailed per-round application remains in round results.
- [Risk] Sequence mode increases prompt complexity. -> Mitigation: inject only the current and previous applied strategy summary, not the entire plan every round.
- [Risk] Existing Supabase Edge Function compatibility path may not understand `strategy_sequence`. -> Mitigation: product frontend continues using the Python API; the legacy path remains compatibility-only for old single-strategy submissions.

## Migration Plan

- Add a nullable `strategy_sequence jsonb` column to `simulation_runs` in both backend and Supabase migrations.
- Deploy backend validation/repository/worker support before exposing the UI control.
- Existing runs keep `strategy_sequence = null` and continue using legacy fields.
- Rollback can hide the UI mode; persisted sequence runs remain readable because completed results are still in existing round and metric tables.
