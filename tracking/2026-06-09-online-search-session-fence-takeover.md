# 2026-06-09: Online Search Request Hits Session Fence Takeover

## Status

Open investigation.

This appears to be the same failure class as the previous Hugging Face Space
session-fence incident, but the exact owned-write path is not yet proven.

## User-Visible Symptom

The user sent this Telegram message to the test bot:

```text
can you search online? tell me what you can find about gemma 4
```

The bot replied with the generic OpenClaw error:

```text
Something went wrong while processing your request. Please try again, or use /new to start a fresh session.
```

## Runtime Context

Space:

```text
osolmaz/onurclawtest
```

Current model configuration at the time of diagnosis:

```text
OPENCLAW_MODEL=huggingface/Qwen/Qwen3-8B
OPENCLAW_MODEL_PROVIDER=huggingface
OPENCLAW_MODEL_BASE_URL=https://router.huggingface.co/v1
```

The Space was running and Telegram connectivity was healthy. The error was not
a Telegram delivery failure.

## Evidence

Space logs show Telegram delivered the inbound message:

```text
2026-06-09T09:57:46.619+00:00 [telegram] Inbound message telegram:7216393410 -> @onurclawtest_bot (direct, 62 chars)
```

The first suspicious state error appeared immediately after dispatch:

```text
2026-06-09T09:57:46.622+00:00 [telegram] message dispatch dedupe store failed: PluginStateStoreError: Failed to register plugin state entry.
```

The embedded agent then failed with the same session-fence error family seen in
the earlier incident:

```text
2026-06-09T09:58:16.068+00:00 [agent/embedded] embedded attempt cleanup detected session takeover after prompt failure; preserving prompt error: runId=8c423f99-218a-4841-a02a-7ee0dac15831 sessionId=2bc0117f-8cd0-43a6-a382-1b4ebc062f6d promptError=session file changed while embedded prompt lock was released: /data/.openclaw/agents/main/sessions/2bc0117f-8cd0-43a6-a382-1b4ebc062f6d.jsonl cleanupError=session file changed while embedded prompt lock was released: /data/.openclaw/agents/main/sessions/2bc0117f-8cd0-43a6-a382-1b4ebc062f6d.jsonl
2026-06-09T09:58:16.069+00:00 [diagnostic] lane task error: lane=main durationMs=21071 error="EmbeddedAttemptSessionTakeoverError: session file changed while embedded prompt lock was released: /data/.openclaw/agents/main/sessions/2bc0117f-8cd0-43a6-a382-1b4ebc062f6d.jsonl"
2026-06-09T09:58:16.070+00:00 [diagnostic] lane task error: lane=session:agent:main:telegram:direct:7216393410 durationMs=21073 error="EmbeddedAttemptSessionTakeoverError: session file changed while embedded prompt lock was released: /data/.openclaw/agents/main/sessions/2bc0117f-8cd0-43a6-a382-1b4ebc062f6d.jsonl"
2026-06-09T09:58:16.073+00:00 Embedded agent failed before reply: session file changed while embedded prompt lock was released: /data/.openclaw/agents/main/sessions/2bc0117f-8cd0-43a6-a382-1b4ebc062f6d.jsonl
```

OpenClaw then sent the generic error response:

```text
2026-06-09T09:58:18.663+00:00 [telegram] outbound send ok accountId=default chatId=7216393410 messageId=42 operation=sendMessage deliveryKind=text chunkCount=1
```

The Telegram offset write also failed:

```text
2026-06-09T09:58:18.708+00:00 [telegram] failed to persist update offset: PluginStateStoreError: Failed to register plugin state entry.
```

## Current Read

What is known:

- Telegram delivered the user message.
- The Space sent the error reply back to Telegram.
- The configured model had already been reverted to `huggingface/Qwen/Qwen3-8B`.
- The failure was an OpenClaw embedded-session fence error.
- Plugin state persistence also failed for Telegram dedupe and update offset.

What is not yet proven:

- Which session writer changed the `.jsonl` file while the prompt lock was
  released.
- Whether the triggering owned-write path is browser/search/tool related,
  Telegram state related, model/tool result related, cleanup related, or another
  session append path.
- Whether the plugin-state failure is causal or only a parallel symptom.

## Relationship to Previous Incident

This is the same class of failure as:

```text
tracking/2026-06-09-session-fence-tool-result-takeover.md
```

The common failure is:

```text
EmbeddedAttemptSessionTakeoverError:
session file changed while embedded prompt lock was released
```

The earlier confirmed problem involved known owned session writes not refreshing
the prompt fence. The Space was then pinned to a newer OpenClaw image containing
the compaction/session-fence fixes available at that time.

This new failure means one of the following is true:

- another owned-write path still does not refresh/publish the session fence;
- the pinned image is still missing a later upstream session/state fix;
- Hugging Face persistent state contains a session/plugin-state condition that
  exposes an already-fixed or partially-fixed path;
- the plugin-state store failure is causing retry/offset behavior that interacts
  badly with embedded session locking.

## Next Investigation Steps

1. Confirm the exact OpenClaw source revision in the running image.
2. Compare that revision against current `openclaw/openclaw` `main` for later
   session, plugin-state, and Telegram persistence fixes.
3. Reproduce locally with a Telegram/direct embedded run that asks for online
   search, ideally using the same image revision.
4. Add a regression test for the specific write path once identified.
5. Rebuild or repin the Space only after the failing path is known, or after
   confirming current main already contains the relevant fix.

## Verification Criteria

The incident is resolved when the Space can complete this Telegram request:

```text
can you search online? tell me what you can find about gemma 4
```

without logging:

```text
EmbeddedAttemptSessionTakeoverError
session file changed while embedded prompt lock was released
```

and without replying with the generic OpenClaw error message.
