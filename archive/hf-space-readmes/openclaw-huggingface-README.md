---
title: OpenClaw on Hugging Face
emoji: 🦞
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
suggested_hardware: cpu-basic
suggested_storage: small
secrets:
  - OPENCLAW_GATEWAY_TOKEN
  - HF_TOKEN
  - TELEGRAM_BOT_TOKEN
  - TELEGRAM_ALLOWED_USERS
  - TELEGRAM_PROXY
  - TELEGRAM_API_ROOT
---

# OpenClaw on Hugging Face

Run a private, fully Hugging Face-hosted OpenClaw gateway from a Docker Space.

This template keeps the runtime in a Hugging Face Space and stores durable state under `/data`, which should be backed by Hugging Face persistent storage. Secrets belong in Space Secrets, not in this repository and not in the persistent volume.

Development and issues: https://github.com/osolmaz/openclaw-huggingface

## Deploy

### Option A: Duplicate this Space

1. Click **Duplicate this Space**.
2. Make the duplicated Space private.
3. Add persistent storage.
4. Set the required Space Secret:
   - `OPENCLAW_GATEWAY_TOKEN`: any long random string for the Control UI.
5. Set model provider secrets as needed:
   - `HF_TOKEN` for Hugging Face Inference Providers.
6. Optional Telegram quick start:
   - `TELEGRAM_BOT_TOKEN`: token from BotFather.
   - `TELEGRAM_ALLOWED_USERS`: your numeric Telegram user ID.
   - `TELEGRAM_PROXY`: optional HTTP/SOCKS proxy if the Space cannot reach `api.telegram.org` directly.
   - `TELEGRAM_API_ROOT`: optional Bot API root for an operator-controlled Telegram Bot API proxy.

After the Space starts, open the Space URL and authenticate with `OPENCLAW_GATEWAY_TOKEN`.

### Option B: Local launcher

For a more automated setup, run the launcher locally after `hf auth login`:

```bash
hf download osolmaz/openclaw-huggingface deploy-hf-openclaw.sh --repo-type space
bash deploy-hf-openclaw.sh
```

The launcher creates a private Space under your Hugging Face account, configures variables and secrets, and leaves credentials on your own machine.

## Runtime Layout

```text
/data/.openclaw/openclaw.json
/data/.openclaw/.env
/data/workspace
/data/backups
```

On first boot, `entrypoint.sh` copies `openclaw.default.json` into `/data/.openclaw/openclaw.json`. Existing user config is never overwritten.

## Notes

- Telegram uses long polling by default, which is the right shape for private Spaces because the Space makes outbound requests to Telegram. Some Hugging Face Space runtimes cannot reach `api.telegram.org` directly; set `TELEGRAM_PROXY` or `TELEGRAM_API_ROOT` when the startup logs show `[telegram-probe] curl getMe failed`.
- Set `OPENCLAW_TELEGRAM_NETWORK_DIAGNOSTICS=1` temporarily to log sanitized DNS, TCP, TLS, and `getMe` diagnostics during startup.
- Set `OPENCLAW_DISCORD_NETWORK_DIAGNOSTICS=1` temporarily to log sanitized Discord REST and Gateway WebSocket diagnostics during startup.
- Webhook-only integrations may require a publicly reachable endpoint.
- Free CPU Spaces are useful for testing, but they may sleep. Use paid hardware for an always-on agent.
