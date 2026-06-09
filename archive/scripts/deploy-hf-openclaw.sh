#!/usr/bin/env bash
set -euo pipefail

TEMPLATE_REPO="${TEMPLATE_REPO:-osolmaz/openclaw-huggingface}"
DEFAULT_SPACE_NAME="openclaw-huggingface"

say() { printf "==> %s\n" "$*"; }
die() { printf "error: %s\n" "$*" >&2; exit 1; }
ask() { local __var="$1"; shift; read -r -p "$* " "$__var"; }
ask_secret() {
  local __var="$1"
  shift
  read -r -s -p "$* " "$__var"
  printf "\n"
}

command -v hf >/dev/null 2>&1 || die "Install the Hugging Face CLI first: https://hf.co/cli"
hf auth whoami >/dev/null 2>&1 || die "Run 'hf auth login' first."

HF_USER="$(hf auth whoami | head -n1 | awk '{print $1}')"
[ -n "$HF_USER" ] || die "Could not determine Hugging Face username."

ask SPACE_NAME "Space name [$DEFAULT_SPACE_NAME]:"
SPACE_NAME="${SPACE_NAME:-$DEFAULT_SPACE_NAME}"
TARGET_REPO="$HF_USER/$SPACE_NAME"

ask_secret GATEWAY_TOKEN "OpenClaw gateway token [leave blank to generate]:"
if [ -z "$GATEWAY_TOKEN" ]; then
  GATEWAY_TOKEN="$(openssl rand -hex 32 2>/dev/null || uuidgen | tr -d '-')"
fi

ask CONFIGURE_TELEGRAM "Configure Telegram now? [y/N]:"
CONFIGURE_TELEGRAM="${CONFIGURE_TELEGRAM:-N}"

TELEGRAM_BOT_TOKEN=""
TELEGRAM_ALLOWED_USERS=""
case "$CONFIGURE_TELEGRAM" in
  y|Y|yes|YES)
    ask_secret TELEGRAM_BOT_TOKEN "Telegram bot token:"
    ask TELEGRAM_ALLOWED_USERS "Numeric Telegram user ID, or comma-separated IDs:"
    ;;
esac

say "Creating private Docker Space: $TARGET_REPO"
hf repo create "$TARGET_REPO" --repo-type space --space-sdk docker --private --yes || true

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

say "Downloading template files"
hf download "$TEMPLATE_REPO" --repo-type space --local-dir "$WORKDIR" >/dev/null

say "Uploading template to $TARGET_REPO"
(
  cd "$WORKDIR"
  git init -q
  git checkout -b main >/dev/null 2>&1 || true
  git add .
  git -c user.name="OpenClaw HF deploy" -c user.email="openclaw@example.invalid" commit -m "feat: initialize OpenClaw Hugging Face Space" >/dev/null
  git remote add origin "https://huggingface.co/spaces/$TARGET_REPO"
  git push -u origin main --force
)

say "Setting Space variables"
hf space variables set "$TARGET_REPO" \
  OPENCLAW_GATEWAY_PORT=7860 \
  OPENCLAW_STATE_DIR=/data/.openclaw \
  OPENCLAW_WORKSPACE_DIR=/data/workspace \
  OPENCLAW_CONFIG_PATH=/data/.openclaw/openclaw.json \
  OPENCLAW_DISABLE_BONJOUR=1

say "Setting Space secrets"
hf space secrets set "$TARGET_REPO" OPENCLAW_GATEWAY_TOKEN="$GATEWAY_TOKEN"

if [ -n "${HF_TOKEN:-}" ]; then
  hf space secrets set "$TARGET_REPO" HF_TOKEN="$HF_TOKEN"
fi

if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
  hf space secrets set "$TARGET_REPO" TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN"
  hf space secrets set "$TARGET_REPO" TELEGRAM_ALLOWED_USERS="$TELEGRAM_ALLOWED_USERS"
fi

cat <<EOF

Created:
  https://huggingface.co/spaces/$TARGET_REPO

Next:
  1. Attach persistent storage to the Space at /data if Hugging Face did not prompt for it.
  2. Open the Space URL after build finishes.
  3. Authenticate with the gateway token you entered/generated.
EOF
