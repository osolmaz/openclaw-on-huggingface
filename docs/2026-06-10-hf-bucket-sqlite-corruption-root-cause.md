# 2026-06-10 HF Bucket SQLite Corruption Root Cause

## Summary

The Hugging Face bucket is not generally corrupt. One SQLite database file stored
on the bucket is corrupt:

```text
/data/.openclaw/state/openclaw.sqlite
```

The failure is a torn SQLite database image. The main DB file says it has 234
pages, but an interior b-tree page in `plugin_state_entries` points to page 235.
Page 235 is not present in the DB file or the current WAL.

That is why Telegram bookkeeping writes fail with OpenClaw's generic
`PluginStateStoreError: Failed to register plugin state entry.` The underlying
SQLite error is `database disk image is malformed`.

## Real DB Evidence

Read-only HF Job:

```text
6a29191bc4f53f9fc5aa3e85
```

Command:

```bash
hf jobs run \
  -v hf://buckets/osolmaz/onurclawtest-data:/data:ro \
  --flavor cpu-basic \
  --timeout 3m \
  python:3.13-slim \
  bash -- -lc 'python - <<'"'"'PY'"'"'
import urllib.request
url="https://raw.githubusercontent.com/osolmaz/openclaw-on-huggingface/55ae103cbb29db739635371346a250a03fcef4c1/repro/hf_bucket_sqlite_wal_repro.py"
open("/tmp/repro.py","wb").write(urllib.request.urlopen(url, timeout=30).read())
PY
python /tmp/repro.py inspect --db /data/.openclaw/state/openclaw.sqlite'
```

Key result:

```json
{
  "integrity_check": "*** in database main ***\nTree 123 page 123 cell 0: invalid page number 235",
  "invalid_child_pointers": [
    {
      "child": 235,
      "header_page_count": 234,
      "kind": 5,
      "page": 123
    }
  ],
  "page_count": 234,
  "raw_header": {
    "header_page_count": 234,
    "page_size": 4096,
    "physical_pages": 234
  }
}
```

The current WAL is only one frame:

```text
openclaw.sqlite-wal size: 4152 bytes
```

That is one WAL frame for one 4096-byte page. Earlier inspection showed it is
for page 121, not page 235. So WAL recovery cannot provide the missing page.

## Independent Repro

The independent repro is in:

```text
repro/hf_bucket_sqlite_wal_repro.py
```

It has no OpenClaw dependency. It only uses Python's standard `sqlite3` module
and raw SQLite page inspection.

The `create-torn` command:

1. Creates a healthy SQLite WAL database with a `plugin_state_entries` table.
2. Verifies the healthy database passes `PRAGMA integrity_check`.
3. Writes a torn copy where the DB header/file contains `N - 1` pages while an
   interior b-tree page still points to page `N`.
4. Verifies SQLite reports the same class of corruption.

HF Job:

```text
6a29190559bbdade52d47bc3
```

Command:

```bash
hf jobs run \
  -v hf://buckets/osolmaz/onurclawtest-data:/data \
  --flavor cpu-basic \
  --timeout 5m \
  python:3.13-slim \
  bash -- -lc 'python - <<'"'"'PY'"'"'
import urllib.request
url="https://raw.githubusercontent.com/osolmaz/openclaw-on-huggingface/55ae103cbb29db739635371346a250a03fcef4c1/repro/hf_bucket_sqlite_wal_repro.py"
open("/tmp/repro.py","wb").write(urllib.request.urlopen(url, timeout=30).read())
PY
python /tmp/repro.py create-torn \
  --db /data/diagnostics/sqlite-torn-repro-20260610-075756/healthy.sqlite \
  --out /data/diagnostics/sqlite-torn-repro-20260610-075756/torn.sqlite \
  --rows 5000 \
  --payload-bytes 2048'
```

Key result:

```json
{
  "source_inspect": {
    "integrity_check": "ok",
    "page_count": 5139
  },
  "torn_inspect": {
    "integrity_check": "*** in database main ***\nTree 2 page 4817 cell 0: invalid page number 5139",
    "invalid_child_pointers": [
      {
        "child": 5139,
        "header_page_count": 5138,
        "kind": 5,
        "page": 4817
      }
    ],
    "page_count": 5138
  }
}
```

This reproduces the same structural SQLite failure without OpenClaw:

```text
interior b-tree page points to a page beyond the DB file/page-count
```

## Negative Test

An independent crash/checkpoint stress run did not reproduce corruption:

```text
6a2917d6c4f53f9fc5aa3e71
```

It ran 150 cases of:

- SQLite WAL mode
- `synchronous=NORMAL`
- plugin-state-shaped inserts
- frequent `PRAGMA wal_checkpoint(TRUNCATE)`
- random process kill
- DB inspection after each kill

Result:

```json
{"bad": [], "bad_count": 0, "cases": 150, "event": "kill-loop-summary"}
```

This means the root cause is not simply "SQLite WAL on HF bucket always corrupts
under process crash." The actual failure is narrower: the durable SQLite family
ended up as a torn image where the main DB file reflects part of a page-growth
operation but not all of it.

## Root Cause

The exact corrupted state is:

```text
main DB header/page count: 234
main DB physical pages:    234
interior b-tree pointer:   235
current WAL frames:        no page 235
```

That can only happen if the persisted SQLite file family lost atomicity across a
page-growth/checkpoint boundary:

- a b-tree parent page that references the new child page became durable;
- the new child page/file growth did not remain durable, or the WAL frame that
  made it valid was later lost/truncated/replaced;
- SQLite then correctly rejected the database as malformed.

The OpenClaw code path that surfaces it is normal plugin state writing:

```text
Telegram dedupe/update-offset write
-> pluginStateRegister/pluginStateRegisterIfAbsent
-> INSERT/UPSERT plugin_state_entries
-> SQLite detects malformed b-tree
```

Telegram did not corrupt the DB. It is just the first active code path that
tries to write the broken table.

## Production Implication

Do not run live SQLite WAL databases directly on the HF bucket mount.

Use one of these instead:

1. Keep live SQLite on local container disk and copy consistent snapshots to the
   bucket.
2. Use a real external database for durable live state.
3. As a temporary mitigation only, reduce SQLite risk by disabling WAL and using
   stricter sync settings, but this does not give the bucket mount local-disk
   semantics.
