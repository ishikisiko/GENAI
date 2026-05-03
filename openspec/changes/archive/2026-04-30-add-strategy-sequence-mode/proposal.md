## Why

Current intervention simulations can only inject one strategy at one selected round, which is useful for simple A/B comparisons but does not model planned multi-step crisis response playbooks. Strategy sequence mode lets users define a per-round intervention plan before a run starts, so the simulator can evaluate coordinated response arcs while preserving the existing fixed-run workflow.

## What Changes

- Add a strategy sequence submission mode for intervention runs where each simulation round can optionally specify a strategy type and message.
- Keep existing single-strategy `strategy_type` + `injection_round` behavior supported for compatibility and simple comparisons.
- Execute worker-owned simulation rounds using the configured per-round strategy when present, recording the applied strategy in existing round results.
- Update the simulation UI to allow users to choose between single intervention and per-round sequence configuration.
- Update comparison/read models so completed sequence runs have clear labels and remain compatible with existing run/result pages.

## Capabilities

### New Capabilities

- `simulation-strategy-sequences`: Per-round planned intervention strategies for simulation runs.

### Modified Capabilities

- `backend-api-boundary`: Simulation submission accepts and validates planned per-round intervention sequences through the Python API.

## Impact

- Backend API request contracts and validation for simulation submissions.
- Simulation repository job payload persistence and worker execution prompts.
- Supabase schema migration for storing optional per-run strategy sequences.
- Frontend simulation form, types, backend client, and comparison labels.
- Backend and frontend tests covering sequence submission, execution, and compatibility.
