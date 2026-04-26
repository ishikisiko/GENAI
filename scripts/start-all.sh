#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${ROOT_DIR}/logs/dev-services"
mkdir -p "${STATE_DIR}"

info() {
  printf '[start-all] %s\n' "$*"
}

fail() {
  printf '[start-all] ERROR: %s\n' "$*" >&2
  exit 1
}

is_running() {
  local pid_file="$1"
  [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null
}

require_file() {
  local path="$1"
  local hint="$2"
  [[ -f "${path}" ]] || fail "Missing ${path}. ${hint}"
}

detect_supabase_port_conflict() {
  local project_id="crisis-sim-local"
  local ports=("54321" "54322" "54323" "54324")
  local conflicts=()
  local line name mapped_port project

  command -v docker >/dev/null 2>&1 || return 0

  while IFS= read -r line; do
    name="${line%%$'\t'*}"
    [[ "${name}" == supabase_* ]] || continue
    [[ "${name}" == *"_${project_id}" ]] && continue

    for mapped_port in "${ports[@]}"; do
      if [[ "${line}" == *":${mapped_port}->"* ]]; then
        conflicts+=("${name} uses ${mapped_port}")
      fi
    done
  done < <(docker ps --format '{{.Names}}	{{.Ports}}' 2>/dev/null || true)

  [[ "${#conflicts[@]}" -eq 0 ]] && return 0

  printf '[start-all] Supabase port conflict detected:\n' >&2
  printf '  - %s\n' "${conflicts[@]}" >&2

  project="${conflicts[0]%% uses *}"
  project="${project##*_}"
  fail "Stop the running Supabase project first: supabase stop --project-id ${project}"
}

resolve_backend_command() {
  local command_name="$1"
  local venv_command="${ROOT_DIR}/backend/.venv/bin/${command_name}"

  if [[ -x "${venv_command}" ]]; then
    printf '%s\n' "${venv_command}"
    return
  fi

  if command -v "${command_name}" >/dev/null 2>&1; then
    command -v "${command_name}"
    return
  fi

  fail "Could not find ${command_name}. From backend/, run: pip install -e \".[dev]\""
}

start_service() {
  local name="$1"
  local cwd="$2"
  shift 2

  local pid_file="${STATE_DIR}/${name}.pid"
  local log_file="${STATE_DIR}/${name}.log"

  if is_running "${pid_file}"; then
    info "${name} already running (pid $(cat "${pid_file}"))."
    return
  fi

  rm -f "${pid_file}"
  info "Starting ${name}; log: ${log_file}"
  (
    cd "${cwd}"
    "$@"
  ) >>"${log_file}" 2>&1 &

  local pid=$!
  printf '%s\n' "${pid}" >"${pid_file}"
  sleep 2

  if ! kill -0 "${pid}" 2>/dev/null; then
    rm -f "${pid_file}"
    tail -n 40 "${log_file}" >&2 || true
    fail "${name} failed to start. See ${log_file}"
  fi
}

command -v npm >/dev/null 2>&1 || fail "npm is required."
require_file "${ROOT_DIR}/.env.local" "Copy .env.local.example to .env.local and fill Supabase values."
require_file "${ROOT_DIR}/backend/.env" "Copy backend/.env.example to backend/.env and set APP_DATABASE_URL."
detect_supabase_port_conflict

info "Starting local Supabase stack..."
(
  cd "${ROOT_DIR}"
  npm run supabase:start
)

BACKEND_API_CMD="$(resolve_backend_command backend-api)"
BACKEND_WORKER_CMD="$(resolve_backend_command backend-worker)"

start_service "backend-api" "${ROOT_DIR}/backend" "${BACKEND_API_CMD}"
start_service "backend-worker" "${ROOT_DIR}/backend" "${BACKEND_WORKER_CMD}"
start_service "frontend" "${ROOT_DIR}" npm run dev:local

cat <<EOF
[start-all] Full local stack is running.
[start-all] Frontend:    http://127.0.0.1:4173
[start-all] Backend API: http://127.0.0.1:8000
[start-all] Supabase:    http://127.0.0.1:54321
[start-all] Studio:      http://127.0.0.1:54323
[start-all] Logs/PIDs:   ${STATE_DIR}
[start-all] Stop with:   npm run stop:all
EOF
