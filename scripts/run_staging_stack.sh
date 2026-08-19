#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE_PATH="${ENV_FILE:-.env.staging}"

OVERRIDE_UVICORN_BIN="${UVICORN_BIN-}"
OVERRIDE_UVICORN_LOG_LEVEL="${UVICORN_LOG_LEVEL-}"
OVERRIDE_UVICORN_ACCESS_LOG="${UVICORN_ACCESS_LOG-}"
OVERRIDE_UVICORN_HOST="${UVICORN_HOST-}"
OVERRIDE_UVICORN_PORT="${UVICORN_PORT-}"
APP_PID=""
TUNNEL_PID=""
source "$ROOT_DIR/scripts/env.sh"

ENV_FILE_PATH="$(resolve_env_file "$ROOT_DIR" "$ENV_FILE_PATH")"
LOCAL_ENV_FILE_PATH="$(env_local_file "$ENV_FILE_PATH")"

cleanup() {
  local exit_code=${1:-0}

  if [[ -n "$TUNNEL_PID" ]] && kill -0 "$TUNNEL_PID" 2>/dev/null; then
    kill "$TUNNEL_PID" 2>/dev/null || true
    wait "$TUNNEL_PID" 2>/dev/null || true
  fi

  if [[ -n "$APP_PID" ]] && kill -0 "$APP_PID" 2>/dev/null; then
    kill "$APP_PID" 2>/dev/null || true
    wait "$APP_PID" 2>/dev/null || true
  fi

  exit "$exit_code"
}

handle_signal() {
  echo
  echo "Encerrando stack de staging..."
  cleanup 0
}

trap handle_signal INT TERM

if [[ ! -f "$ENV_FILE_PATH" ]]; then
  echo "Arquivo de ambiente nao encontrado: $ENV_FILE_PATH" >&2
  exit 1
fi
cd "$ROOT_DIR"

load_env_file "$ENV_FILE_PATH"
load_env_file "$LOCAL_ENV_FILE_PATH"

UVICORN_BIN="${OVERRIDE_UVICORN_BIN:-${UVICORN_BIN:-$ROOT_DIR/.venv/bin/uvicorn}}"
UVICORN_LOG_LEVEL="${OVERRIDE_UVICORN_LOG_LEVEL:-${UVICORN_LOG_LEVEL:-warning}}"
UVICORN_ACCESS_LOG="${OVERRIDE_UVICORN_ACCESS_LOG:-${UVICORN_ACCESS_LOG:-false}}"
UVICORN_HOST="${OVERRIDE_UVICORN_HOST:-${UVICORN_HOST:-127.0.0.1}}"
UVICORN_PORT="${OVERRIDE_UVICORN_PORT:-${UVICORN_PORT:-8000}}"

if [[ ! -x "$UVICORN_BIN" ]]; then
  echo "uvicorn nao encontrado em $UVICORN_BIN. Rode make install primeiro." >&2
  exit 1
fi

assert_uvicorn_port_free() {
  local host="$1"
  local port="$2"

  if ! python3 - "$host" "$port" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.2)
    try:
        sock.bind((host, port))
    except OSError as exc:
        print(exc)
        raise SystemExit(1)
PY
  then
    return 1
  fi
  return 0
}

if ! assert_uvicorn_port_free "$UVICORN_HOST" "$UVICORN_PORT"; then
  echo "A porta ${UVICORN_PORT} no host ${UVICORN_HOST} esta em uso."
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$UVICORN_PORT" -sTCP:LISTEN -n -P | head -n 5
  fi
  echo
  echo "Opcao rapida:"
  echo "  UVICORN_PORT=<outra porta> make staging"
  echo "ex: UVICORN_PORT=8001 make staging"
  echo
  echo "Se quiser manter 8000, encerre o processo que esta ocupando a porta e rode novamente."
  exit 1
fi

echo "Subindo API staging com $ENV_FILE_PATH"
if [[ -f "$LOCAL_ENV_FILE_PATH" ]]; then
  echo "Aplicando overrides locais de $LOCAL_ENV_FILE_PATH"
fi
UVICORN_ENV_ARGS=()
while IFS= read -r arg; do
  UVICORN_ENV_ARGS+=("$arg")
done < <(merged_env_args "$ENV_FILE_PATH" "$LOCAL_ENV_FILE_PATH")

UVICORN_RUNTIME_ARGS=(--reload --reload-include ".env*" --log-level "$UVICORN_LOG_LEVEL")
UVICORN_RUNTIME_ARGS+=(--host "$UVICORN_HOST" --port "$UVICORN_PORT")
case "${UVICORN_ACCESS_LOG}" in
  true|TRUE|1|yes|YES)
    ;;
  *)
    UVICORN_RUNTIME_ARGS+=(--no-access-log)
    ;;
esac

export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:${PYTHONPATH}}"
"$UVICORN_BIN" --app-dir "$ROOT_DIR/src" app.main:app "${UVICORN_ENV_ARGS[@]}" "${UVICORN_RUNTIME_ARGS[@]}" &
APP_PID=$!

TUNNEL_ENABLED="${STAGING_TUNNEL_ENABLED:-auto}"
TUNNEL_ENABLED="$(printf '%s' "$TUNNEL_ENABLED" | tr '[:upper:]' '[:lower:]')"
case "$TUNNEL_ENABLED" in
  true|1|yes|on)
    if [[ -z "${CLOUDFLARE_TUNNEL_HOSTNAME:-}" ]]; then
      echo "STAGING_TUNNEL_ENABLED=true, mas CLOUDFLARE_TUNNEL_HOSTNAME nao esta definido." >&2
      cleanup 1
    fi
    echo "Subindo tunnel staging"
    ;;
  false|0|off|disabled|no)
    echo "Tunnel staging desabilitado por STAGING_TUNNEL_ENABLED=${TUNNEL_ENABLED}"
    ;;
  *)
    if [[ -z "${CLOUDFLARE_TUNNEL_HOSTNAME:-}" ]]; then
      echo "CLOUDFLARE_TUNNEL_HOSTNAME nao definido: seguindo com API staging sem tunnel."
      echo "Se quiser habilitar tunnel, defina CLOUDFLARE_TUNNEL_HOSTNAME em .env.staging.local."
    else
      echo "Subindo tunnel staging"
    fi
    ;;
esac

if [[ -n "${CLOUDFLARE_TUNNEL_HOSTNAME:-}" ]] && [[ "$TUNNEL_ENABLED" != "false" && "$TUNNEL_ENABLED" != "0" && "$TUNNEL_ENABLED" != "off" && "$TUNNEL_ENABLED" != "disabled" && "$TUNNEL_ENABLED" != "no" ]]; then
  ENV_FILE="$ENV_FILE_PATH" CLOUDFLARE_TUNNEL_URL="${CLOUDFLARE_TUNNEL_URL:-http://$UVICORN_HOST:$UVICORN_PORT}" \
    "$ROOT_DIR/scripts/run_dev_tunnel.sh" &
  TUNNEL_PID=$!
fi

while true; do
  if ! kill -0 "$APP_PID" 2>/dev/null; then
    wait "$APP_PID"
    APP_STATUS=$?
    echo "API staging encerrou com status $APP_STATUS." >&2
    cleanup "$APP_STATUS"
  fi

  if [[ -n "$TUNNEL_PID" ]] && ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
    wait "$TUNNEL_PID"
    TUNNEL_STATUS=$?
    echo "Tunnel staging encerrou com status $TUNNEL_STATUS." >&2
    cleanup "$TUNNEL_STATUS"
  fi

  sleep 1
done
