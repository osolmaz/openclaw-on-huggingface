# Decisions

## Tracking Repo

Create a public GitHub tracking repo:

```text
osolmaz/openclaw-on-huggingface
```

This repo tracks deployment work and verification. It does not own OpenClaw core
fixes.

## Runtime Fix Location

OpenClaw runtime/session-lock fixes belong in:

```text
openclaw/openclaw
```

## Space Verification

Verify OpenClaw fixes on an actual Hugging Face Space before changing the public
template.

Use a temporary image:

```text
ghcr.io/osolmaz/openclaw:hf-session-fence-test
```

Then switch back to the official OpenClaw image after upstream release.

## Telegram Mode

Private Spaces should use Telegram long polling, not webhooks.

Reason: private Spaces cannot receive unauthenticated public webhook requests,
but they can make outbound polling requests.

## Space Hardware

Paid HF Space hardware resolved the earlier Telegram egress/TLS failure in the
test deployment. That was separate from the OpenClaw session-fence bug.
