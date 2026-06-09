# OpenClaw Hugging Face Deployment Template: Implementation Plan

## Decision

Create one generic Hugging Face Docker Space template under:

```text
osolmaz/openclaw-huggingface
```

The template is not Telegram-specific. It runs a fully Hugging Face-hosted OpenClaw gateway/control UI, with Telegram as the first optional happy-path channel.

## Maintained Resources

Maintained by us:

```text
1 public HF Space template:
  osolmaz/openclaw-huggingface
```

Created per user:

```text
1 private duplicated HF Space
1 persistent /data volume or private HF storage attachment
```

## Repository Contents

```text
README.md
Dockerfile
entrypoint.sh
openclaw.default.json
deploy-hf-openclaw.sh
scripts/
  configure-telegram.mjs
```

## Runtime Contract

The Space runs OpenClaw from the official image:

```text
ghcr.io/openclaw/openclaw:latest
```

It exposes the Hugging Face Space port:

```text
OPENCLAW_GATEWAY_PORT=7860
```

Persistent state lives under:

```text
OPENCLAW_STATE_DIR=/data/.openclaw
OPENCLAW_WORKSPACE_DIR=/data/workspace
OPENCLAW_CONFIG_PATH=/data/.openclaw/openclaw.json
```

Secrets live in Hugging Face Space Secrets:

```text
OPENCLAW_GATEWAY_TOKEN
HF_TOKEN
TELEGRAM_BOT_TOKEN
TELEGRAM_ALLOWED_USERS
```

## First-Boot Behavior

`entrypoint.sh`:

1. Creates `/data/.openclaw`, `/data/workspace`, and `/data/backups`.
2. Copies `openclaw.default.json` to `/data/.openclaw/openclaw.json` only if no config exists.
3. If Telegram secrets are present, enables Telegram in config and inserts the allowlist.
4. Starts `openclaw gateway`.

Existing user config is never overwritten.

## User Flows

### Secure default: duplicate in Hugging Face UI

1. User opens the public template Space.
2. User clicks **Duplicate this Space**.
3. User makes the duplicated Space private.
4. User adds persistent storage.
5. User enters Space Secrets.
6. Space builds and starts.
7. User opens Control UI or messages the configured Telegram bot.

### Automated path: local launcher

1. User runs `hf auth login`.
2. User downloads and runs `deploy-hf-openclaw.sh`.
3. Script creates a private Space under the user's own HF account.
4. Script uploads template files and sets variables/secrets.
5. User attaches storage if needed and opens the Space.

This avoids a hosted launcher that asks for Hugging Face credentials.

## Security Defaults

- No credentials in git.
- No credentials in `/data` by default.
- Private duplicated Spaces for real use.
- Gateway auth required via `OPENCLAW_GATEWAY_TOKEN`.
- Telegram uses `dmPolicy: "allowlist"` when configured by the helper.
- Telegram long polling works with private Spaces because the runtime connects outbound.

## Open Questions To Validate

1. Confirm the exact OpenClaw config schema for `gateway.auth.token` with `${OPENCLAW_GATEWAY_TOKEN}` substitution.
2. Confirm the official Docker image contains the `openclaw` CLI on PATH for `openclaw gateway`.
3. Confirm Hugging Face persistent storage can be requested/suggested cleanly from Space metadata, or document the manual attach step.
4. Confirm `hf space variables set` and `hf space secrets set` command syntax against the installed CLI version before publishing the launcher.
5. Decide whether to pin `ghcr.io/openclaw/openclaw:<version>` instead of `latest` for reproducible template builds.

## Next Implementation Steps

1. Install/authenticate Hugging Face CLI locally.
2. Create `osolmaz/openclaw-huggingface` as a public Docker Space.
3. Push the scaffold.
4. Duplicate it into a private test Space.
5. Attach persistent storage at `/data`.
6. Set `OPENCLAW_GATEWAY_TOKEN`, `HF_TOKEN`, and Telegram secrets.
7. Verify:
   - Build succeeds.
   - `/health` returns healthy.
   - Control UI accepts the gateway token.
   - `/data/.openclaw/openclaw.json` persists across restart.
   - Telegram DM from allowed user reaches OpenClaw.
   - Telegram DM from non-allowed user is rejected.
8. Iterate on config/schema issues.
9. Freeze a tested image tag.
10. Update README with the exact working duplicate and launcher instructions.
