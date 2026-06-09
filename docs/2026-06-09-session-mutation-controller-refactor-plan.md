# 2026-06-09: Session Mutation Controller Refactor Plan

## Goal

Eliminate the recurring OpenClaw embedded-session takeover failures caused by
OpenClaw-owned session writes that are invisible to the embedded session fence.

The target end state is simple:

```text
If OpenClaw changes a session file, the write lock and session fence are updated
in the same operation.
```

This is an OpenClaw core fix. Hugging Face Spaces are the production-like
verification environment, not the cause of the bug.

## Problem

The embedded runner correctly protects session files from external concurrent
writes. It does this by remembering a session-file fingerprint while the prompt
lock is released and checking that fingerprint later.

The problem is that OpenClaw itself mutates the same session file from multiple
places:

```text
message_end persistence
tool call / tool result persistence
auto-compaction
orphaned user-message repair
transcript rewrites
hook and maintenance writes
cleanup/finalization writes
```

Some of those writes publish the new owned fingerprint. Some do not. When they
do not, OpenClaw later mistakes its own write for an external takeover and sends
the generic channel error after a model response.

## Design Rule

Raw session mutation must not be available inside embedded runs.

Embedded code should not call these directly:

```text
sessionManager.appendMessage(...)
sessionManager.appendCustomEntry(...)
sessionManager.branch(...)
sessionManager.resetLeaf()
flushSessionManagerFile(...)
rewriteTranscript(...)
```

Instead, embedded code should call one mutation API that owns:

```text
1. acquire or reuse the session write lock
2. assert the current session-file fence
3. read the pre-write fingerprint
4. apply the mutation
5. flush the session file if needed
6. publish the OpenClaw-owned fingerprint
7. refresh in-memory session state
8. release the lock
```

## Proposed API

Introduce a controller near the embedded runner lock code:

```text
src/agents/embedded-agent-runner/run/session-mutation-controller.ts
```

Working shape:

```ts
await sessionMutations.run("repair-orphaned-user-message", async (session) => {
  session.branch(parentId);
  session.appendMessage(userMessage);
});
```

The caller provides the reason and the mutation body. The controller handles
locking, fingerprint publication, file flush, and state refresh.

The mutation reason should be structured enough for logs and tests:

```text
message_end
tool_result
auto_compaction
orphan_user_repair
transcript_rewrite
hook_write
maintenance
cleanup
```

## Implementation Plan

### Phase 1: Inventory All Embedded Session Mutations

Audit direct and indirect mutation call sites under:

```text
src/agents/embedded-agent-runner/
src/agents/sessions/
src/agents/context-engine/
```

Search targets:

```text
appendMessage(
appendCustomEntry(
branch(
resetLeaf(
flushSessionManagerFile(
rewriteTranscript
withSessionWriteLock(
publishOwnedWrite
```

Classify each mutation as:

```text
prompt-time write
post-prompt write
cleanup write
maintenance write
test-only write
non-embedded write
```

Deliverable:

```text
docs or PR notes listing every embedded mutation path and its migration status
```

### Phase 2: Add SessionMutationController

Build the controller on top of the existing session lock controller instead of
adding a second lock system.

Required behavior:

```text
run(reason, mutation)
runSync(reason, mutation)
refreshActiveSessionState()
log mutation reason, runId, sessionId
publish owned-write fence after successful mutation
preserve takeover detection for non-owned external writes
```

Nested writes must be safe. If a mutation is already inside an active write
lock, the controller should reuse it and still publish the owned fingerprint
once the mutation changes the file.

### Phase 3: Migrate Confirmed Failing Paths

Migrate the paths that have already failed on the Hugging Face Space:

```text
auto-compaction transcript append
message_end persistence
orphaned trailing user-message repair
tool call / tool result persistence
```

Acceptance for this phase:

```text
The current Telegram session can answer repeated messages without
EmbeddedAttemptSessionTakeoverError.
```

### Phase 4: Migrate Remaining Embedded Mutation Paths

Migrate the rest of the embedded runner write paths:

```text
before_agent_run blocked-message persistence
prompt cache custom entries
session yield artifacts
mid-turn precheck cleanup
context-engine maintenance rewrites
bootstrap completion entries
agent steering lease/session entries
manual compaction boundary writes
transcript rewrite helpers
cleanup/finalization writes
```

Do not leave mixed ownership where some embedded writes use the controller and
nearby writes still call `SessionManager` directly.

### Phase 5: Make Misuse Hard

After migration, make direct embedded mutations visibly wrong.

Options, from lightest to strongest:

```text
add comments and tests around forbidden direct writes
add a repo-local lint/script check for direct SessionManager writes in embedded runner files
hide raw SessionManager behind a narrower embedded-session interface
make the controller the only object passed into mutation-heavy embedded code
```

Preferred production path:

```text
Use a narrow embedded-session mutation interface and add a script test that
fails if new direct mutation calls are introduced under embedded runner code.
```

### Phase 6: Regression Tests for the Bug Class

Add tests that prove the class is fixed, not only the latest incident.

Minimum regression cases:

```text
1. OpenClaw-owned prompt-time append while prompt lock is released does not trip takeover.
2. Auto-compaction append during prompt execution does not trip takeover.
3. message_end persistence during prompt execution does not trip takeover.
4. Orphaned trailing user repair followed by a new prompt does not trip takeover.
5. Tool call / tool result persistence does not trip takeover.
6. External file mutation still trips takeover.
```

The last case is critical. The refactor must not disable real takeover
protection.

### Phase 7: Production Verification on Hugging Face

Build an OpenClaw image from the fixed branch and pin the test Space to it.

Verify with:

```text
Space: osolmaz/onurclawtest
Telegram bot: existing private test bot
Model: huggingface/Qwen/Qwen3-8B
Persistent bucket: osolmaz/onurclawtest-data
```

Test messages:

```text
which model are you
please continue
can you search online? tell me what you can find about gemma 4
/new
please continue
```

Pass criteria:

```text
No EmbeddedAttemptSessionTakeoverError in Space logs.
No generic channel error appended after a successful model response.
Session JSONL contains coherent user/assistant turns.
External-write takeover regression test still passes locally.
```

## Expected Size

This is a large but bounded refactor:

```text
3-5 focused engineering days for implementation
1-2 weeks if including careful review, hardening, and production verification
20-40 files touched
1,000-2,500 changed lines, mostly tests and call-site migration
```

## Risks

The main risk is weakening real concurrency protection. The controller must make
OpenClaw-owned writes safe without accepting arbitrary file changes.

Secondary risks:

```text
changing local CLI behavior
breaking compaction or transcript branching
missing an indirect write path
introducing deadlocks through nested write locks
publishing a fence for a failed or partial write
```

## Non-Goals

This plan does not require:

```text
rewriting the session file format
removing append-only transcript semantics
changing Hugging Face storage
changing Telegram delivery
changing model provider
disabling tools
```

## Definition of Done

The refactor is complete when:

```text
1. Embedded session mutations go through the controller.
2. Direct embedded `SessionManager` writes are blocked or test-detected.
3. Regression tests cover owned writes and real external takeover.
4. The Hugging Face Space completes repeated Telegram prompts without the
   generic post-response error.
5. The implementation is merged into OpenClaw core and the Space is pinned to a
   fixed image.
```
