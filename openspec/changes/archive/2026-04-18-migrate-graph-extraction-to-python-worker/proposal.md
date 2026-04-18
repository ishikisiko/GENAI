## Why

The current graph extraction flow is still owned by the API/runtime path, which makes extraction orchestration, status handling, and future NLP evolution harder to isolate and scale. Moving the pipeline into the Python worker now gives the second major business flow a durable job boundary and a clearer place to extend document-level extraction, normalization, and merge logic.

## What Changes

- Move `extract-graph` execution from the API-owned path to a Python worker-owned extraction pipeline.
- Limit the API layer to validating requests, creating extraction jobs, and exposing job status needed by existing callers and UI state.
- Introduce a worker pipeline with explicit stages for document input loading, per-document extraction, normalization, graph merge, and persistence.
- Keep the externally visible semantics of persisted `entities`, `relations`, and `claims` as stable as possible while changing internal execution ownership.
- Add extension points so later NLP and graph-processing steps can be inserted without redesigning the extraction flow again.

## Capabilities

### New Capabilities
- `graph-extraction-pipeline`: Defines the worker-owned extraction pipeline, including stage boundaries, merge behavior, and persistence expectations for graph extraction jobs.

### Modified Capabilities
- `job-processing-foundation`: Extraction work is created as durable jobs by the API and executed by workers with canonical lifecycle tracking.

## Impact

- Python API endpoints and service code that currently trigger `extract-graph`
- Python worker job handlers and shared backend modules
- Persistence logic for extraction outputs, normalization, and merge
- Job payload/status surfaces consumed by the frontend for extraction state display
