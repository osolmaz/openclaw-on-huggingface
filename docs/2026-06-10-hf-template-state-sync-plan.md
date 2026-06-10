# 2026-06-10 HF Template State Sync Plan

## Decision

The long-term Hugging Face deployment should use:

```text
local live state + bucket snapshots
```

not:

```text
live SQLite directly on the HF bucket mount
```

The bucket remains the durable source of truth. The Space container restores a
verified state snapshot from the bucket on boot, runs OpenClaw against local
disk, and writes verified snapshots back to the bucket.

## Repository Ownership

This tracking repo is not the final runtime source of truth.

Target ownership:

```text
github.com/osolmaz/openclaw-huggingface
  Source of truth for the HF Space template:
  - TypeScript state sync implementation
  - tests
  - Dockerfile
  - entrypoint
  - template config
  - release/sync tooling

huggingface.co/spaces/osolmaz/openclaw-huggingface
  Built deployable Space template artifact.
  This should be generated/synced from the GitHub source repo.

huggingface.co/osolmaz/openclaw-bootstrap
  Minimal bootstrap launcher.
  It creates the user's private bucket and private Space, copies the template,
  and sets secrets/env vars. It should not contain runtime state logic.

user private bucket
  Durable state snapshots, config, and recovery manifests.

user private Space
  Runtime copy of the template.
```

## Why This Is The Right Split

- GitHub is the right place for maintainable TypeScript, tests, review, and CI.
- The HF Space is the deployable artifact, not the hand-maintained source.
- The bootstrap repo stays small and security-sensitive: no users paste HF
  credentials into another Space.
- Users do not need Python locally.
- The Space runtime uses Node, which OpenClaw already requires.
- HF-specific storage behavior stays outside OpenClaw core until the pattern is
  proven.

## Runtime Layout

Inside the Space:

```text
/data/
  openclaw-state/
    manifest.json
    snapshots/
      state-2026-06-10T12-00-00Z.tar.zst
      state-2026-06-10T12-05-00Z.tar.zst
    locks/
    tmp/

/tmp/openclaw-live/
  .openclaw/
    openclaw.json
    state/openclaw.sqlite
    agents/
    credentials/
    ...
```

OpenClaw should run with:

```text
OPENCLAW_STATE_DIR=/tmp/openclaw-live/.openclaw
OPENCLAW_CONFIG_PATH=/tmp/openclaw-live/.openclaw/openclaw.json
OPENCLAW_WORKSPACE_DIR=/tmp/openclaw-live/workspace
```

The bucket path under `/data/openclaw-state` stores snapshots and manifests only,
not the active SQLite database.

## TypeScript Components

In `github.com/osolmaz/openclaw-huggingface`:

```text
src/hf-state-sync/
  cli.ts
  restore.ts
  snapshot.ts
  manifest.ts
  sqlite.ts
  paths.ts
  archive.ts
  lock.ts
  retention.ts

test/
  hf-state-sync.restore.test.ts
  hf-state-sync.snapshot.test.ts
  hf-state-sync.manifest.test.ts
  hf-state-sync.sqlite.test.ts

space/
  Dockerfile
  entrypoint.sh
  openclaw.default.json
  scripts/
    configure-telegram.mjs
```

Built artifact inside the image:

```text
/app/hf-state-sync.js
```

Entrypoint shape:

```bash
node /app/hf-state-sync.js restore
node /app/hf-state-sync.js supervise -- openclaw gateway
```

`supervise` starts OpenClaw, runs the snapshot loop, forwards signals, and takes
a best-effort final snapshot on shutdown.

## Snapshot Contract

Manifest:

```json
{
  "version": 1,
  "current": {
    "id": "2026-06-10T12-00-00Z",
    "path": "snapshots/state-2026-06-10T12-00-00Z.tar.zst",
    "createdAt": "2026-06-10T12:00:00.000Z",
    "sha256": "...",
    "sizeBytes": 123456,
    "openclawVersion": "...",
    "verified": true
  },
  "previous": []
}
```

Rules:

- Never overwrite the only known-good snapshot.
- Write new snapshots to a temp path first.
- Verify archive checksum.
- Verify every SQLite DB included in the snapshot with `PRAGMA integrity_check`.
- Promote by replacing `manifest.json` only after verification passes.
- Keep the last N verified snapshots.
- If the latest snapshot is bad on boot, try previous snapshots in order.

## SQLite Handling

Snapshotting must not copy live SQLite files directly.

For each live SQLite DB:

```text
*.sqlite
*.sqlite-wal
*.sqlite-shm
```

Use SQLite backup semantics:

1. Open the live DB read-only or read-write as required by the backup method.
2. Produce a consistent standalone DB file in a staging directory.
3. Run `PRAGMA integrity_check` on the staged DB.
4. Put the staged DB into the archive.

Acceptable implementation options:

- Prefer SQLite backup API if available cleanly from Node.
- Otherwise use `VACUUM INTO` against the live DB into staging.
- Avoid raw copying of `sqlite`, `sqlite-wal`, and `sqlite-shm` as the durable
  snapshot format.

## Files To Include

Snapshot the whole OpenClaw state directory, not only `state/openclaw.sqlite`.

Include:

```text
openclaw.json
.env if present and intentionally managed by this template
agent-name.txt
agents/
credentials/
state/*.sqlite as consistent standalone DB copies
workspace metadata if stored under state
```

Exclude:

```text
state/*.sqlite-wal
state/*.sqlite-shm
logs that do not need durability
tmp/
cache/
large transient downloads
```

The exclude list should be explicit and tested.

## Bootstrap Behavior

`osolmaz/openclaw-bootstrap` should:

1. Resolve the bot name and target resource names.
2. Create a private bucket.
3. Create/copy a private Space from `osolmaz/openclaw-huggingface`.
4. Set Space secrets and variables.
5. Start/restart the Space.
6. Print the Space URL and bucket URL.

It should not implement snapshot/restore logic.

## Verification

Required tests in the GitHub source repo:

- fresh boot with empty bucket creates initial local state
- snapshot writes manifest only after verification
- restore chooses latest verified snapshot
- restore falls back when latest snapshot fails integrity
- SQLite snapshot does not include WAL/SHM sidecars
- corrupted SQLite archive is rejected
- retention keeps last N snapshots
- signal handling runs best-effort final snapshot
- bootstrap-created Space uses `/tmp/openclaw-live`, not `/data/.openclaw`, as
  `OPENCLAW_STATE_DIR`

Required live HF verification:

1. Deploy template to a private test Space.
2. Confirm OpenClaw state DB lives under `/tmp/openclaw-live`.
3. Confirm bucket contains snapshots and manifest, not active WAL sidecars.
4. Send Telegram messages and verify replies.
5. Restart/rebuild the Space.
6. Confirm state restores from bucket snapshot.
7. Run read-only integrity checks against restored local DB and latest bucket
   snapshot.

## Migration From Current Test Space

The current test bucket contains a corrupted live DB. Do not use it as a trusted
snapshot.

For migration testing:

1. Start with a fresh bucket, or
2. recover non-SQLite state from the old bucket manually, and
3. create a fresh SQLite state DB locally.

The new template should refuse to promote a snapshot if SQLite integrity fails.

## Open Questions

- Snapshot interval default: likely 30-60 seconds for Telegram UX.
- Whether to snapshot immediately after important plugin-state writes is an
  OpenClaw-core concern and should not be required for the first HF wrapper.
- Whether to use `tar.zst` or `tar.gz` depends on what the final image includes.
  Prefer `tar.zst` if `zstd` is available; otherwise use `tar.gz`.
- Whether secrets should live in snapshots at all. Prefer HF Space secrets for
  provider tokens; snapshot only runtime state that must persist.

## First Implementation Target

Create the source repo:

```text
github.com/osolmaz/openclaw-huggingface
```

Then implement the TypeScript state sync layer, tests, and Space template there.
After that, sync the built template to:

```text
huggingface.co/spaces/osolmaz/openclaw-huggingface
```
