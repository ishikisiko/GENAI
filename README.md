# CrisisSim Local Setup

This project can run fully against a local Supabase stack. The app uses:

- local Postgres via Supabase
- local Auth via Supabase
- local Edge Functions for graph extraction, agent generation, and simulation
- local Vite frontend pointed at the local Supabase API

## Prerequisites

- Docker Desktop, Rancher Desktop, Podman, or another Docker-compatible runtime
- Node.js 20+

Supabase local development uses the CLI plus a local container runtime, per the official docs:
https://supabase.com/docs/guides/local-development

## One-time setup

1. Install dependencies:

```bash
npm install
```

2. Copy the frontend env template:

```bash
cp .env.local.example .env.local
```

3. Copy the function secrets template:

```bash
cp supabase/functions/.env.example supabase/functions/.env
```

4. Start local Supabase:

```bash
npm run supabase:start
```

5. Get the local keys:

```bash
npm run supabase:status
```

6. Update the copied env files with the values from `supabase status`:

- `.env.local`
  - `VITE_SUPABASE_URL=http://127.0.0.1:54321`
  - `VITE_SUPABASE_ANON_KEY=<local anon key>`
- `supabase/functions/.env`
  - `SUPABASE_URL=http://127.0.0.1:54321`
  - `SUPABASE_SERVICE_ROLE_KEY=<local service_role key>`
  - `LLM_API_KEY=<your LLM key>`
  - `LLM_MODEL=<your model, default gpt-4o-mini>`
  - `LLM_BASE_URL=<OpenAI-compatible base URL, default https://api.openai.com/v1>`
  - `LLM_PROVIDER=<openai|anthropic>`

The Supabase docs note that `supabase/functions/.env` is auto-loaded for local function serving, and you can also pass a custom file with `--env-file`:
https://supabase.com/docs/guides/functions/secrets

## Daily local workflow

Start the local Supabase stack:

```bash
npm run supabase:start
```

Serve the Edge Functions locally:

```bash
npm run supabase:functions:serve
```

In another terminal, start the frontend:

```bash
npm run dev:local
```

The local services are:

- API: `http://127.0.0.1:54321`
- Studio: `http://127.0.0.1:54323`
- Frontend: `http://127.0.0.1:4173`

## Resetting local data

To rebuild the local database from the migration files:

```bash
npm run supabase:db:reset
```

This reapplies the SQL files under [supabase/migrations](/root/code/Genai/supabase/migrations).

## Notes

- `supabase/config.toml` is included so the repo is ready for local CLI usage.
- The frontend uses `.env.local`, so you do not need to overwrite the existing `.env` that points at the hosted project.
- The local stack still requires an OpenAI-compatible LLM configuration if you want the three Edge Functions to actually generate outputs.
- All three functions now read LLM config from one shared layer:
  - `LLM_API_KEY`
  - `LLM_MODEL`
  - `LLM_BASE_URL`
- Anthropic-compatible endpoints are also supported via:
  - `LLM_PROVIDER=anthropic`
  - `ANTHROPIC_BASE_URL`
  - `ANTHROPIC_MODEL`
  - `ANTHROPIC_VERSION`
- `OPENAI_API_KEY` is still accepted as a fallback for backward compatibility.
- A bug in `run-simulation` was fixed so the function loads the crisis case by `id`, not `case_id`.

## Useful commands

```bash
npm run supabase:start
npm run supabase:status
npm run supabase:functions:serve
npm run supabase:db:reset
npm run supabase:stop
npm run dev:local
```
