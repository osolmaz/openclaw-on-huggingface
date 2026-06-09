# 2026-06-09 Auto-Compaction Session Fence Takeover

## Summary

The Telegram message `please continue` reached the Hugging Face Space, but
OpenClaw returned the generic channel error.

The root cause was OpenClaw auto-compaction appending a compaction row while the
embedded prompt lock was released. The session fence then saw that the session
file metadata changed and treated OpenClaw's own compaction write as an external
session takeover.

## Evidence

Space logs around `2026-06-09T12:19:39Z` showed:

```text
embedded run auto-compaction start
embedded run auto-compaction complete
EmbeddedAttemptSessionTakeoverError: session file changed while embedded prompt lock was released
```

The session JSONL did not contain the failed user message. The only new row
around the failure was a compaction row:

```text
type: compaction
timestamp: 2026-06-09T12:19:53.744Z
tokensBefore: 27339
```

## Fix

Local OpenClaw commit:

```text
53e662fba3 fix(agents): publish auto-compaction transcript writes
```

The fix lets `AgentSession` publish its auto-compaction append as an owned
session write, so the embedded session fence advances to the new file state
instead of raising takeover.

Regression coverage was added in:

```text
src/agents/embedded-agent-runner/run/attempt.session-lock.test.ts
```

## Validation

Local tests:

```text
pnpm exec vitest run src/agents/embedded-agent-runner/run/attempt.session-lock.test.ts
pnpm tsgo:core:test
```

Both passed.

The fixed image is deployed to the private Hugging Face test Space:

```text
Space: osolmaz/onurclawtest
Space commit: 0251267002af2274cdd289185f2beaf053ae084b
Image: ghcr.io/osolmaz/openclaw-live-test:hf-53e662fb
Digest: sha256:3f729e1a9c74c885a3f05b3ad4ee48f072a84b02654d9374e4dc304bb610abeb
```

Startup verification passed: Telegram `getMe` succeeded, gateway started, and
Telegram polling started.
