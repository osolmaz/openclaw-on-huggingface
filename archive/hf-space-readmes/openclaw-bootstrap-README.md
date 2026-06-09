---
tags:
  - openclaw
  - bootstrap
  - agent
  - huggingface-spaces
library_name: openclaw
---

# OpenClaw Bootstrap

One-shot bootstrap for deploying a private OpenClaw gateway on Hugging Face.

```bash
bash <(curl -fsSL https://huggingface.co/osolmaz/openclaw-bootstrap/resolve/main/bootstrap.sh)
```

The bootstrap creates:

- a private Hugging Face Docker Space from `osolmaz/openclaw-huggingface`
- a private Hugging Face Storage Bucket
- a read-write bucket mount at `/data`
- Space secrets for the gateway token, Hugging Face token, and optional Telegram bot

The resulting OpenClaw runtime is hosted on Hugging Face. Persistent state lives in the private bucket. Secrets stay in Hugging Face Space Secrets.

## Prerequisites

- Hugging Face CLI installed as `hf`
- `hf auth login` completed
- Optional Telegram bot token from BotFather
- Optional `TELEGRAM_PROXY` or `OPENCLAW_TELEGRAM_PROXY` if your Hugging Face Space cannot reach `api.telegram.org` directly
- Optional `TELEGRAM_API_ROOT` or `OPENCLAW_TELEGRAM_API_ROOT` for an operator-controlled Telegram Bot API proxy root

## Notes

- The generated Space is private by default.
- Telegram is allowlisted by default; do not make a personal agent open to everyone.
- The script reads the HF token with `hf auth token`, not Python package imports.
- Private Spaces should use Telegram long polling, not webhooks. Telegram cannot call a private Space webhook because Hugging Face requires Space access through Hugging Face auth.
- If the deployed Space logs `[telegram-probe] curl getMe failed` or Telegram `UND_ERR_CONNECT_TIMEOUT`, Hugging Face egress to Telegram is unavailable from that runtime. Rerun the bootstrap with `TELEGRAM_PROXY` set to a reachable HTTP/SOCKS proxy or `TELEGRAM_API_ROOT` set to a reachable Bot API proxy root.
