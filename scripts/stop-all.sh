#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${ROOT_DIR}/logs/dev-services"
BACKEND_WORKER_UNIT="genai-backend-worker.service"

info() {
  printf '[stop-all] %s\n' "$*"
}

stop_service() {
  local name="$1"
  local pid_file="${STATE_DIR}/${name}.pid"

  if [[ ! -f "${pid_file}" ]]; then
    info "${name} pid file not found; skipping."
    return
  fi

  local pid
  pid="$(cat "${pid_file}")"

  if ! kill -0 "${pid}" 2>/dev/null; then
    info "${name} is not running; removing stale pid file."
    rm -f "${pid_file}"
    return
  fi

  info "Stopping ${name} (pid ${pid})..."
  terminate_tree "${pid}" TERM

  for _ in {1..15}; do
    if ! kill -0 "${pid}" 2>/dev/null; then
      rm -f "${pid_file}"
      info "${name} stopped."
      return
    fi
    sleep 1
  done

  info "${name} did not exit gracefully; forcing stop."
  terminate_tree "${pid}" KILL
  rm -f "${pid_file}"
}

systemd_unit_available() {
  command -v systemctl >/dev/null 2>&1 && systemctl cat "${BACKEND_WORKER_UNIT}" >/dev/null 2>&1
}

stop_backend_worker() {
  if systemd_unit_available; then
    if systemctl is-active --quiet "${BACKEND_WORKER_UNIT}"; then
      info "Stopping backend-worker via systemd (${BACKEND_WORKER_UNIT})..."
      systemctl stop "${BACKEND_WORKER_UNIT}"
    else
      info "backend-worker systemd service is not active."
    fi
  fi

  stop_service "backend-worker"
}

terminate_tree() {
  local pid="$1"
  local signal="$2"

  if command -v pgrep >/dev/null 2>&1; then
    local child
    while read -r child; do
      [[ -n "${child}" ]] && terminate_tree "${child}" "${signal}"
    done < <(pgrep -P "${pid}" || true)
  fi

  kill "-${signal}" "${pid}" 2>/dev/null || true
}

stop_service "frontend"
stop_backend_worker
stop_service "backend-api"

if command -v npm >/dev/null 2>&1; then
  info "Stopping local Supabase stack..."
  (
    cd "${ROOT_DIR}"
    npm run supabase:stop
  )
else
  info "npm not found; Supabase stack was not stopped."
fi

info "Done."
