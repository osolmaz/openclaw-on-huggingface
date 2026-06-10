#!/usr/bin/env python3
"""Reproduce and diagnose SQLite WAL behavior on Hugging Face bucket mounts.

This script intentionally has no OpenClaw dependency. It only uses Python's
standard sqlite3 module and raw SQLite page inspection.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
import string
import struct
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


PAGE_HEADER_SIZE = 100


def connect(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path, timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA wal_autocheckpoint=1000")
    return con


def create_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS plugin_state_entries (
          plugin_id TEXT NOT NULL,
          namespace TEXT NOT NULL,
          entry_key TEXT NOT NULL,
          value_json TEXT NOT NULL,
          created_at INTEGER NOT NULL,
          expires_at INTEGER,
          PRIMARY KEY (plugin_id, namespace, entry_key)
        );
        CREATE INDEX IF NOT EXISTS idx_plugin_state_expiry
          ON plugin_state_entries(expires_at)
          WHERE expires_at IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_plugin_state_listing
          ON plugin_state_entries(plugin_id, namespace, created_at, entry_key);
        """
    )
    con.commit()


def value_payload(writer: str, seq: int, size: int) -> str:
    return json.dumps(
        {
            "writer": writer,
            "seq": seq,
            "payload": (writer + "-" + string.ascii_letters) * max(1, size // 53),
        },
        separators=(",", ":"),
    )


def writer(args: argparse.Namespace) -> None:
    path = Path(args.db)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = connect(path)
    create_schema(con)

    writer_id = args.writer_id or str(os.getpid())
    deadline = time.monotonic() + args.seconds
    inserted = 0
    errors: list[dict[str, str]] = []
    print_json({"event": "writer-start", "writer": writer_id, "db": str(path)})
    while time.monotonic() < deadline:
        try:
            con.execute("BEGIN IMMEDIATE")
            now = int(time.time() * 1000)
            for _ in range(args.batch_size):
                inserted += 1
                key = f"{writer_id}:{inserted:012d}"
                con.execute(
                    """
                    INSERT INTO plugin_state_entries (
                      plugin_id, namespace, entry_key, value_json, created_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(plugin_id, namespace, entry_key) DO UPDATE SET
                      value_json=excluded.value_json,
                      created_at=excluded.created_at,
                      expires_at=excluded.expires_at
                    """,
                    (
                        "telegram",
                        "dedupe",
                        key,
                        value_payload(writer_id, inserted, args.payload_bytes),
                        now + inserted,
                        None,
                    ),
                )
            con.commit()
            if inserted % args.checkpoint_every == 0:
                con.execute(f"PRAGMA wal_checkpoint({args.checkpoint_mode})").fetchall()
        except Exception as exc:  # noqa: BLE001 - diagnostics should keep running
            errors.append({"type": type(exc).__name__, "message": str(exc)})
            try:
                con.rollback()
            except Exception:
                pass
            time.sleep(random.uniform(0.01, 0.2))
    if args.final_checkpoint:
        try:
            con.execute(f"PRAGMA wal_checkpoint({args.checkpoint_mode})").fetchall()
        except Exception as exc:  # noqa: BLE001
            errors.append({"type": type(exc).__name__, "message": str(exc)})
    con.close()
    print_json(
        {
            "event": "writer-done",
            "writer": writer_id,
            "inserted": inserted,
            "errors": errors[:20],
            "error_count": len(errors),
        }
    )


def run_kill_loop(args: argparse.Namespace) -> None:
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    bad: list[dict[str, Any]] = []
    script = Path(__file__).resolve()
    for index in range(args.cases):
        db = root / f"case-{index:04d}.sqlite"
        remove_sqlite_family(db)
        proc = subprocess.Popen(
            [
                sys.executable,
                str(script),
                "writer",
                "--db",
                str(db),
                "--seconds",
                str(args.writer_seconds),
                "--writer-id",
                f"kill-{index}",
                "--batch-size",
                str(args.batch_size),
                "--payload-bytes",
                str(args.payload_bytes),
                "--checkpoint-every",
                str(args.checkpoint_every),
                "--checkpoint-mode",
                args.checkpoint_mode,
                "--final-checkpoint",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(random.uniform(args.min_kill_delay, args.max_kill_delay))
        proc.kill()
        proc.wait(timeout=10)
        result = inspect_database(db)
        print_json({"event": "case", "index": index, "result": result})
        if not result["ok"]:
            bad.append({"index": index, "result": result})
    print_json({"event": "kill-loop-summary", "cases": args.cases, "bad_count": len(bad), "bad": bad[:10]})


def remove_sqlite_family(db: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        try:
            db.with_name(db.name + suffix).unlink()
        except FileNotFoundError:
            pass


def inspect_database(path: Path) -> dict[str, Any]:
    files = {
        suffix or "main": file_info(path.with_name(path.name + suffix))
        for suffix in ("", "-wal", "-shm")
    }
    result: dict[str, Any] = {"path": str(path), "files": files}
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
        try:
            result["journal_mode"] = con.execute("PRAGMA journal_mode").fetchone()[0]
            result["page_size"] = con.execute("PRAGMA page_size").fetchone()[0]
            result["page_count"] = con.execute("PRAGMA page_count").fetchone()[0]
            result["integrity_check"] = con.execute("PRAGMA integrity_check").fetchone()[0]
            result["row_count"] = con.execute("SELECT COUNT(*) FROM plugin_state_entries").fetchone()[0]
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        result["sqlite_error"] = {"type": type(exc).__name__, "message": str(exc)}
        try:
            con = sqlite3.connect(f"file:{path}?immutable=1", uri=True, timeout=10)
            try:
                result["immutable_journal_mode"] = con.execute("PRAGMA journal_mode").fetchone()[0]
                result["immutable_page_size"] = con.execute("PRAGMA page_size").fetchone()[0]
                result["immutable_page_count"] = con.execute("PRAGMA page_count").fetchone()[0]
                result["immutable_integrity_check"] = con.execute("PRAGMA integrity_check").fetchone()[0]
            finally:
                con.close()
        except Exception as immutable_exc:  # noqa: BLE001
            result["immutable_sqlite_error"] = {
                "type": type(immutable_exc).__name__,
                "message": str(immutable_exc),
            }

    raw = inspect_raw_pages(path)
    result.update(raw)
    result["ok"] = result.get("integrity_check") == "ok" and not raw.get("invalid_child_pointers")
    return result


def find_child_pointer_to_page(data: bytes, page_size: int, target_page: int) -> dict[str, int] | None:
    physical_pages = len(data) // page_size
    for page_no in range(1, physical_pages + 1):
        start = (page_no - 1) * page_size
        hdr = start + (PAGE_HEADER_SIZE if page_no == 1 else 0)
        if hdr >= len(data):
            continue
        page_type = data[hdr]
        if page_type not in (0x02, 0x05):
            continue
        cell_count = int.from_bytes(data[hdr + 3 : hdr + 5], "big")
        right_child = int.from_bytes(data[hdr + 8 : hdr + 12], "big")
        if right_child == target_page:
            return {"page": page_no, "kind": page_type, "right_child": right_child}
        cell_ptr_base = hdr + 12
        for cell_index in range(cell_count):
            ptr = int.from_bytes(data[cell_ptr_base + cell_index * 2 : cell_ptr_base + cell_index * 2 + 2], "big")
            absolute = start + ptr
            if absolute + 4 > len(data):
                continue
            child = int.from_bytes(data[absolute : absolute + 4], "big")
            if child == target_page:
                return {"page": page_no, "kind": page_type, "cell": cell_index, "child": child}
    return None


def create_torn_checkpoint_signature(args: argparse.Namespace) -> None:
    db = Path(args.db)
    out = Path(args.out)
    remove_sqlite_family(db)
    remove_sqlite_family(out)
    db.parent.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)

    con = connect(db)
    create_schema(con)
    inserted = 0
    while inserted < args.rows:
        con.execute("BEGIN IMMEDIATE")
        now = int(time.time() * 1000)
        for _ in range(args.batch_size):
            inserted += 1
            con.execute(
                """
                INSERT INTO plugin_state_entries (
                  plugin_id, namespace, entry_key, value_json, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "telegram",
                    "dedupe",
                    f"torn:{inserted:012d}",
                    value_payload("torn", inserted, args.payload_bytes),
                    now + inserted,
                    None,
                ),
            )
            if inserted >= args.rows:
                break
        con.commit()
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()
    con.close()

    data = bytearray(db.read_bytes())
    page_size = struct.unpack(">H", data[16:18])[0]
    if page_size == 1:
        page_size = 65536
    page_count = struct.unpack(">I", data[28:32])[0]
    if page_count < 2:
        raise SystemExit("database did not grow enough to make a torn copy")

    pointer = find_child_pointer_to_page(bytes(data), page_size, page_count)
    if pointer is None:
        raise SystemExit(
            f"could not find an interior b-tree pointer to final page {page_count}; "
            "increase --rows or --payload-bytes"
        )

    torn_page_count = page_count - 1
    data[28:32] = torn_page_count.to_bytes(4, "big")
    torn_size = torn_page_count * page_size
    out.write_bytes(data[:torn_size])
    print_json(
        {
            "event": "create-torn",
            "source": str(db),
            "out": str(out),
            "rows": inserted,
            "original_page_count": page_count,
            "torn_page_count": torn_page_count,
            "pointer_to_removed_page": pointer,
            "source_inspect": inspect_database(db),
            "torn_inspect": inspect_database(out),
        }
    )


def file_info(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    return {"exists": True, "size": stat.st_size, "mtime": stat.st_mtime}


def inspect_raw_pages(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size < PAGE_HEADER_SIZE:
        return {}
    data = path.read_bytes()
    if data[:16] != b"SQLite format 3\x00":
        return {"raw_error": "not a sqlite3 database"}
    page_size = struct.unpack(">H", data[16:18])[0]
    if page_size == 1:
        page_size = 65536
    header_page_count = struct.unpack(">I", data[28:32])[0]
    physical_pages = len(data) // page_size
    invalid: list[dict[str, int]] = []
    interior_pages = 0
    for page_no in range(1, physical_pages + 1):
        start = (page_no - 1) * page_size
        hdr = start + (PAGE_HEADER_SIZE if page_no == 1 else 0)
        if hdr >= len(data):
            continue
        page_type = data[hdr]
        if page_type not in (0x02, 0x05):
            continue
        interior_pages += 1
        cell_count = int.from_bytes(data[hdr + 3 : hdr + 5], "big")
        right_child = int.from_bytes(data[hdr + 8 : hdr + 12], "big")
        if right_child > header_page_count:
            invalid.append(
                {
                    "page": page_no,
                    "kind": page_type,
                    "child": right_child,
                    "header_page_count": header_page_count,
                }
            )
        cell_ptr_base = hdr + 12
        for cell_index in range(cell_count):
            ptr = int.from_bytes(data[cell_ptr_base + cell_index * 2 : cell_ptr_base + cell_index * 2 + 2], "big")
            absolute = start + ptr
            if absolute + 4 > len(data):
                continue
            child = int.from_bytes(data[absolute : absolute + 4], "big")
            if child > header_page_count:
                invalid.append(
                    {
                        "page": page_no,
                        "kind": page_type,
                        "cell": cell_index,
                        "child": child,
                        "header_page_count": header_page_count,
                    }
                )
    return {
        "raw_header": {
            "page_size": page_size,
            "header_page_count": header_page_count,
            "physical_pages": physical_pages,
        },
        "interior_page_count": interior_pages,
        "invalid_child_pointers": invalid,
    }


def inspect_command(args: argparse.Namespace) -> None:
    print_json({"event": "inspect", "result": inspect_database(Path(args.db))})


def print_json(value: dict[str, Any]) -> None:
    print(json.dumps(value, sort_keys=True), flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    writer_parser = sub.add_parser("writer")
    writer_parser.add_argument("--db", required=True)
    writer_parser.add_argument("--seconds", type=float, default=60)
    writer_parser.add_argument("--writer-id", default="")
    writer_parser.add_argument("--batch-size", type=int, default=25)
    writer_parser.add_argument("--payload-bytes", type=int, default=2048)
    writer_parser.add_argument("--checkpoint-every", type=int, default=1000)
    writer_parser.add_argument("--checkpoint-mode", default="TRUNCATE", choices=["PASSIVE", "FULL", "RESTART", "TRUNCATE"])
    writer_parser.add_argument("--final-checkpoint", action="store_true")
    writer_parser.set_defaults(func=writer)

    kill_parser = sub.add_parser("kill-loop")
    kill_parser.add_argument("--root", required=True)
    kill_parser.add_argument("--cases", type=int, default=100)
    kill_parser.add_argument("--writer-seconds", type=float, default=30)
    kill_parser.add_argument("--min-kill-delay", type=float, default=0.02)
    kill_parser.add_argument("--max-kill-delay", type=float, default=1.0)
    kill_parser.add_argument("--batch-size", type=int, default=25)
    kill_parser.add_argument("--payload-bytes", type=int, default=2048)
    kill_parser.add_argument("--checkpoint-every", type=int, default=1000)
    kill_parser.add_argument("--checkpoint-mode", default="TRUNCATE", choices=["PASSIVE", "FULL", "RESTART", "TRUNCATE"])
    kill_parser.set_defaults(func=run_kill_loop)

    inspect_parser = sub.add_parser("inspect")
    inspect_parser.add_argument("--db", required=True)
    inspect_parser.set_defaults(func=inspect_command)

    torn_parser = sub.add_parser("create-torn")
    torn_parser.add_argument("--db", required=True, help="Healthy source database to create")
    torn_parser.add_argument("--out", required=True, help="Torn/corrupt database copy to write")
    torn_parser.add_argument("--rows", type=int, default=5000)
    torn_parser.add_argument("--batch-size", type=int, default=50)
    torn_parser.add_argument("--payload-bytes", type=int, default=2048)
    torn_parser.set_defaults(func=create_torn_checkpoint_signature)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
