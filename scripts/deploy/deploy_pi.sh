#!/usr/bin/env bash
set -euo pipefail

# Deploy MomirPrinter from macOS/Linux host to a Raspberry Pi over SSH.
# Tries multiple targets so the same command works in home-WiFi and AP mode.

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PI_USER="${PI_USER:-pi}"
PI_TARGETS=(
  "mo.local"
  "10.42.0.1"
  "192.168.4.1"
)
PI_DEST="${PI_DEST:-~/Mo}"
SERVICE_NAME="${SERVICE_NAME:-momir}"
SSH_OPTS=(
  -o BatchMode=yes
  -o ConnectTimeout=4
  -o StrictHostKeyChecking=accept-new
)

EXCLUDES=(
  --exclude momir_env
  --exclude node_modules
  --exclude /images
  --exclude /cards_json
  --exclude raw_cards
  --exclude AtomicCards.json
  --exclude .git
  --exclude .DS_Store
)

usage() {
  cat <<'EOF'
Usage: scripts/deploy_pi.sh [--target <host>] [--dry-run]

Environment overrides:
  PI_USER=<user>           Default: pi
  PI_DEST=<remote_path>    Default: ~/MomirPrinter
  SERVICE_NAME=<name>      Default: momir

Examples:
  scripts/deploy_pi.sh
  PI_USER=pi scripts/deploy_pi.sh --target momirpi.local
  scripts/deploy_pi.sh --dry-run
EOF
}

DRY_RUN=0
FORCED_TARGET=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      FORCED_TARGET="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

pick_target() {
  local target
  if [[ -n "$FORCED_TARGET" ]]; then
    echo "$FORCED_TARGET"
    return 0
  fi

  for target in "${PI_TARGETS[@]}"; do
    if ssh "${SSH_OPTS[@]}" "${PI_USER}@${target}" "echo ok" >/dev/null 2>&1; then
      echo "$target"
      return 0
    fi
  done

  return 1
}

TARGET="$(pick_target || true)"
if [[ -z "$TARGET" ]]; then
  echo "Could not reach Pi via any target: ${PI_TARGETS[*]}" >&2
  echo "Connect your Mac to the right network and retry." >&2
  exit 2
fi

echo "Deploy target: ${PI_USER}@${TARGET}:${PI_DEST}"

RSYNC_FLAGS=(-av --delete)
if [[ "$DRY_RUN" -eq 1 ]]; then
  RSYNC_FLAGS+=(--dry-run)
  echo "Running in dry-run mode"
fi

rsync "${RSYNC_FLAGS[@]}" \
  "${EXCLUDES[@]}" \
  "$PROJECT_ROOT/" "${PI_USER}@${TARGET}:${PI_DEST}/"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "Dry-run complete"
  exit 0
fi

# Restart service if present, otherwise print manual run command.
if ssh "${PI_USER}@${TARGET}" "systemctl list-unit-files | grep -q '^${SERVICE_NAME}.service'"; then
  ssh "${PI_USER}@${TARGET}" "sudo systemctl restart ${SERVICE_NAME} && sudo systemctl --no-pager --full status ${SERVICE_NAME} | sed -n '1,15p'"
else
  echo "Service '${SERVICE_NAME}' not installed on Pi yet."
  echo "Install it with scripts/install_momir_service.sh on the Pi, or run Flask manually."
fi

echo "Deploy complete."
echo "Try: http://${TARGET}:8000"
