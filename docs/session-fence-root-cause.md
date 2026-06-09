# Session Fence Root Cause

## Summary

The Telegram reply failure is an OpenClaw embedded-session locking bug.

It is not caused by Telegram delivery, Hugging Face network egress, Hugging Face
Spaces as a product, Qwen, or Hugging Face Inference Providers.

## Observed Failure

User message:

```text
which model are you
```

The Space received the Telegram message. OpenClaw sent it to:

```text
huggingface/Qwen/Qwen3-8B
```

The model called:

```text
session_status
```

The tool returned successfully with:

```text
Model: huggingface/Qwen/Qwen3-8B
```

Then OpenClaw aborted the run with:

```text
EmbeddedAttemptSessionTakeoverError:
session file changed while embedded prompt lock was released
```

The user saw the generic channel error:

```text
Something went wrong while processing your request.
```

## Evidence

Live Space logs showed:

```text
[telegram] Inbound message telegram:<allowed-user-id> -> @<telegram-bot>
embedded attempt cleanup detected session takeover after prompt failure
EmbeddedAttemptSessionTakeoverError: session file changed while embedded prompt lock was released
```

The session JSONL showed this sequence:

```text
user: which model are you
assistant: toolCall session_status
toolResult: session_status ok, model huggingface/Qwen/Qwen3-8B
assistant: generic error delivery mirror
```

The trajectory showed the run ending with:

```text
status: error
promptError: session file changed while embedded prompt lock was released
```

## What Changed

OpenClaw's session fence compares the session file fingerprint using:

```text
dev
ino
size
mtimeNs
ctimeNs
```

For this failure, OpenClaw appended its own transcript entries while the prompt
lock was released:

```text
assistant tool call
tool result
```

That changes file size and timestamps. The fence later treated the changed
fingerprint as a session takeover.

## Exact Problem

OpenClaw changed the session file itself, but the embedded prompt fence did not
accept the resulting file state as the valid current state.

The fence should distinguish:

```text
OpenClaw-owned transcript progress
```

from:

```text
external/session-takeover mutation
```

In this case it treated OpenClaw-owned transcript progress as takeover.

## Proper Fix

Fix OpenClaw core session handling in:

```text
src/agents/embedded-agent-runner/run/attempt.session-lock.ts
```

The fix must preserve real takeover protection while accepting valid OpenClaw
internal transcript writes during model/tool execution.

Also audit non-message session writes such as compaction and custom entries,
because normal message writes use the guarded persistence path but not every
session-file write does.

## Non-Fixes

These are workarounds or distractions, not the proper fix:

- Disabling tools for the model.
- Deleting the session.
- Making the Space public.
- Blaming Telegram.
- Blaming Hugging Face Inference Providers.
- Copying source into a running container.
