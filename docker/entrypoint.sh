#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/app"
STATE_DIR="${APP_DIR}/runtime"
DISPLAY_NUM="${DISPLAY_NUM:-99}"
export DISPLAY=":${DISPLAY_NUM}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
VNC_PORT="${VNC_PORT:-5900}"

log() {
  echo "[entrypoint] $*"
}

# App uses: os.environ.get("TESTNET") or user.cfg — any non-empty TESTNET env wins, and
# python-binance treats the string "false" as testnet enabled. Unset misleading values.
case "${TESTNET:-}" in
  false|False|0|no|NO) unset TESTNET ;;
esac

# Prefer mounted user.cfg for Binance keys when both are set (avoids -2014 from stale .env).
if [[ -f "${APP_DIR}/user.cfg" ]]; then
  if grep -qE '^[[:space:]]*api_key[[:space:]]*=.+' "${APP_DIR}/user.cfg" 2>/dev/null; then
    if [[ -n "${API_KEY:-}" ]]; then
      log "user.cfg defines api_key; unsetting API_KEY from environment"
      unset API_KEY
    fi
  fi
  if grep -qE '^[[:space:]]*api_secret_key[[:space:]]*=.+' "${APP_DIR}/user.cfg" 2>/dev/null; then
    if [[ -n "${API_SECRET_KEY:-}" ]]; then
      log "user.cfg defines api_secret_key; unsetting API_SECRET_KEY from environment"
      unset API_SECRET_KEY
    fi
  fi
fi

has_binance_credentials() {
  if [[ -n "${API_KEY:-}" && -n "${API_SECRET_KEY:-}" ]]; then
    return 0
  fi
  if [[ -f "${APP_DIR}/user.cfg" ]]; then
    if grep -qE '^[[:space:]]*api_key[[:space:]]*=.+' "${APP_DIR}/user.cfg" 2>/dev/null \
      && grep -qE '^[[:space:]]*api_secret_key[[:space:]]*=.+' "${APP_DIR}/user.cfg" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

setup_state_volume() {
  mkdir -p "${STATE_DIR}"

  local state_files=(
    profit_gain_state.json
    bot_status.json
    gui_state.json
  )
  for file_name in "${state_files[@]}"; do
    touch "${STATE_DIR}/${file_name}"
    ln -sfn "${STATE_DIR}/${file_name}" "${APP_DIR}/${file_name}"
  done

  local flag_files=(
    cooldown.flag
    bb_std.flag
    reset_trades.flag
    add_trade.flag
    force_sell.flag
    update_pending.flag
  )
  for flag_name in "${flag_files[@]}"; do
    touch "${STATE_DIR}/${flag_name}"
    ln -sfn "${STATE_DIR}/${flag_name}" "${APP_DIR}/${flag_name}"
  done

  mkdir -p "${APP_DIR}/data" "${APP_DIR}/logs"
}

validate_config() {
  if ! has_binance_credentials; then
    log "ERROR: Binance credentials missing."
    log "Set API_KEY and API_SECRET_KEY in .env, or mount config/user.cfg with api_key and api_secret_key."
    exit 1
  fi

  if [[ ! -f "${APP_DIR}/supported_coin_list.txt" ]]; then
    if [[ -f "${APP_DIR}/supported_coin_list.exemple" ]]; then
      log "WARN: supported_coin_list.txt not found; copying from supported_coin_list.exemple"
      cp "${APP_DIR}/supported_coin_list.exemple" "${APP_DIR}/supported_coin_list.txt"
    else
      log "ERROR: supported_coin_list.txt not found. Mount config/supported_coin_list.txt"
      exit 1
    fi
  fi

  if [[ ! -s "${APP_DIR}/supported_coin_list.txt" ]]; then
    log "ERROR: supported_coin_list.txt is empty."
    exit 1
  fi
}

setup_vnc_password() {
  mkdir -p "${STATE_DIR}/.vnc"
  local passwd_file="${STATE_DIR}/.vnc/passwd"
  if [[ -z "${VNC_PASSWORD:-}" ]]; then
    VNC_PASSWORD="$(openssl rand -hex 8)"
    log "WARN: VNC_PASSWORD not set; generated ephemeral password: ${VNC_PASSWORD}"
  fi
  x11vnc -storepasswd "${VNC_PASSWORD}" "${passwd_file}" >/dev/null 2>&1
}

cleanup_display_artifacts() {
  rm -f "/tmp/.X${DISPLAY_NUM}-lock" "/tmp/.X11-unix/X${DISPLAY_NUM}" 2>/dev/null || true
  mkdir -p /tmp/.X11-unix
  chmod 1777 /tmp/.X11-unix 2>/dev/null || true
}

start_display_stack() {
  cleanup_display_artifacts
  log "Starting Xvfb on ${DISPLAY}..."
  Xvfb "${DISPLAY}" -screen 0 1280x800x24 -ac +extension GLX +render -noreset &
  XVFB_PID=$!
  sleep 1

  if ! kill -0 "${XVFB_PID}" 2>/dev/null; then
    log "ERROR: Xvfb failed to start."
    exit 1
  fi

  log "Starting fluxbox..."
  fluxbox >/dev/null 2>&1 &

  setup_vnc_password
  log "Starting x11vnc on port ${VNC_PORT}..."
  x11vnc -display "${DISPLAY}" -forever -shared -rfbport "${VNC_PORT}" \
    -rfbauth "${STATE_DIR}/.vnc/passwd" -noxdamage >/dev/null 2>&1 &

  local novnc_web="/usr/share/novnc"
  if [[ ! -d "${novnc_web}" ]]; then
    novnc_web="/usr/share/nodejs/novnc"
  fi
  if [[ ! -d "${novnc_web}" ]]; then
    log "ERROR: noVNC web assets not found."
    exit 1
  fi

  log "Starting noVNC on 0.0.0.0:${NOVNC_PORT} (open http://localhost:${NOVNC_PORT}/vnc.html)"
  websockify --web="${novnc_web}" "0.0.0.0:${NOVNC_PORT}" "localhost:${VNC_PORT}" >/tmp/websockify.log 2>&1 &
  sleep 1
  if ! pgrep -f "websockify.*${NOVNC_PORT}" >/dev/null; then
    log "ERROR: websockify failed to start. Log:"
    tail -n 20 /tmp/websockify.log 2>/dev/null || true
    exit 1
  fi
}

cd "${APP_DIR}"
setup_state_volume
validate_config
start_display_stack

log "Launching painel.py..."
python3.11 "${APP_DIR}/painel.py" &
PAINEL_PID=$!

# Keep container alive for noVNC even if painel exits (logs remain visible via docker logs)
wait "${PAINEL_PID}" || log "WARN: painel.py exited with code $?."
log "Container staying up for noVNC access; restart with: docker compose restart bot"
wait -n 2>/dev/null || tail -f /dev/null
