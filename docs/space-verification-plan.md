# Hugging Face Space Verification Plan

Goal: prove the OpenClaw session-fence fix works in the real Hugging Face Space
environment.

## Preconditions

- The OpenClaw fix exists in a branch of `openclaw/openclaw`.
- Regression tests pass locally in OpenClaw.
- A temporary container image has been pushed:

```text
ghcr.io/osolmaz/openclaw-live-test:hf-5e1fbca3
```

## Space Change

Update the test Space Dockerfile from:

```dockerfile
FROM ghcr.io/openclaw/openclaw:2026.6.5-beta.13
```

to:

```dockerfile
FROM ghcr.io/osolmaz/openclaw-live-test:hf-5e1fbca3
```

Use the private test Space first:

```text
osolmaz/onurclawtest
```

Do not update the public template until the test Space passes.

Current test Space commit:

```text
58551d6a638bef36d2c5968c1c5d2f9f31480b0e
```

Current status as of `2026-06-09`: build succeeded, Space is `RUNNING`, gateway
is ready, and Telegram polling started.

## Verification

1. Rebuild the Space.
2. Confirm startup logs show Telegram connectivity:

```text
fetch getMe ok
starting provider (@<telegram-bot>)
```

3. Send this Telegram DM from the configured allowed Telegram user:

```text
which model are you
```

4. Expected reply:

```text
huggingface/Qwen/Qwen3-8B
```

Exact wording can vary, but it must be a normal assistant response, not the
generic error.

5. Confirm Space logs do not contain:

```text
EmbeddedAttemptSessionTakeoverError
session file changed while embedded prompt lock was released
```

6. Confirm the session JSONL contains:

```text
user message
assistant session_status tool call
session_status tool result
assistant final answer
```

7. Send a second normal message and confirm it is processed without delay or
generic error.

## Pass Criteria

The fix is verified on Spaces only when all of these are true:

- Telegram message reaches OpenClaw.
- The model can use `session_status`.
- OpenClaw continues after the tool result.
- The user receives a normal assistant reply.
- No session takeover error appears in logs.
- The session JSONL shows a complete tool-call turn.
