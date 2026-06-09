# Current Bug: Embedded Session Fence Rejects Valid Tool Progress

## Status

Active. This blocks reliable Telegram replies for the Hugging Face-hosted
OpenClaw test deployment when the model uses tools.

## What Happens

1. Telegram delivers the user's DM to the Hugging Face Space.
2. OpenClaw starts an embedded run with `huggingface/Qwen/Qwen3-8B`.
3. The model calls `session_status`.
4. `session_status` succeeds and returns the current model:

```text
huggingface/Qwen/Qwen3-8B
```

5. OpenClaw aborts before sending the final assistant reply:

```text
EmbeddedAttemptSessionTakeoverError:
session file changed while embedded prompt lock was released
```

6. The user receives the generic error message instead of the assistant reply.

## Root Cause

OpenClaw's embedded session fence treats OpenClaw-owned transcript progress
during model/tool execution as a session takeover.

The fence compares the session JSONL file fingerprint:

```text
dev
ino
size
mtimeNs
ctimeNs
```

During the run, OpenClaw appends valid internal transcript entries such as the
assistant tool call and tool result. Those writes change the file fingerprint.
The fence later rejects the changed fingerprint instead of accepting it as the
new valid OpenClaw-owned session state.

## Correct Fix Location

OpenClaw core:

```text
src/agents/embedded-agent-runner/run/attempt.session-lock.ts
```

Related write paths to audit:

```text
src/agents/session-tool-result-guard.ts
src/agents/session-tool-result-guard-wrapper.ts
src/agents/sessions/session-manager.ts
src/agents/sessions/agent-session.ts
```

## Required Verification

The fix is verified only when a Hugging Face Space running the patched OpenClaw
image can complete this Telegram turn:

```text
User: which model are you
Model: calls session_status
Tool: returns model status
Assistant: sends a normal final reply
```

The Space logs must not contain:

```text
EmbeddedAttemptSessionTakeoverError
session file changed while embedded prompt lock was released
```
