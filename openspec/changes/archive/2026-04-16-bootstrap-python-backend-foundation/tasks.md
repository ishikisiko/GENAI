## 1. Backend Workspace Setup

- [x] 1.1 Create the new Python backend workspace and select the project/dependency management baseline
- [x] 1.2 Add the shared package layout for API, worker, domain, infrastructure, and tests
- [x] 1.3 Add local developer tooling for dependency install, formatting, linting, and test execution

## 2. Shared Runtime Foundations

- [x] 2.1 Implement typed configuration loading and startup validation for backend services
- [x] 2.2 Implement structured logging with shared correlation fields for request and job execution contexts
- [x] 2.3 Implement the shared application error model and API-safe error response mapping

## 3. Database and Persistence Layer

- [x] 3.1 Add migration tooling for the backend and establish the database migration workflow
- [x] 3.2 Create the `jobs` and `job_attempts` schema with indexes, foreign keys, and lifecycle metadata
- [x] 3.3 Implement the shared database access layer and reusable transaction/session primitives

## 4. Job Processing Foundation

- [x] 4.1 Implement job repository methods for create, claim, complete, fail, cancel, and retry transitions
- [x] 4.2 Implement transactional worker claim logic that creates `job_attempts` records safely under contention
- [x] 4.3 Add worker runtime scaffolding for polling, executing, and recording attempt outcomes

## 5. Operations Surface

- [x] 5.1 Add liveness and readiness endpoints with dependency-aware readiness checks
- [x] 5.2 Add a basic operations endpoint for safe runtime metadata and aggregate job status visibility
- [x] 5.3 Ensure health and operations failures emit structured logs using the shared conventions

## 6. Integration Boundaries and Verification

- [x] 6.1 Document the retained Supabase responsibilities for Postgres, Auth, RLS, and optional Realtime
- [x] 6.2 Add tests for configuration validation, health endpoints, and job state transition rules
- [x] 6.3 Validate that the new backend foundation lands without changing existing frontend call chains or Edge Function business logic
