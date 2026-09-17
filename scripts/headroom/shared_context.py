from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from headroom import SharedContext


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_store_path() -> Path:
    return repo_root() / ".headroom" / "shared-context.json"


class ProjectSharedContext:
    def __init__(self, store_path: Path, model: str, ttl: int, max_entries: int) -> None:
        self.store_path = store_path
        self.model = model
        self.ttl = ttl
        self.max_entries = max_entries
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return {"model": self.model, "ttl": self.ttl, "max_entries": self.max_entries, "entries": {}}
        payload = json.loads(self.store_path.read_text(encoding="utf-8"))
        payload.setdefault("entries", {})
        payload.setdefault("model", self.model)
        payload.setdefault("ttl", self.ttl)
        payload.setdefault("max_entries", self.max_entries)
        return payload

    def _save(self, payload: dict[str, Any]) -> None:
        self.store_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _active_entries(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = time.time()
        entries = payload.get("entries", {})
        active = {key: entry for key, entry in entries.items() if now - float(entry.get("timestamp", 0)) <= self.ttl}
        payload["entries"] = active
        return active

    def put(self, key: str, content: str, agent: str | None = None) -> dict[str, Any]:
        payload = self._load()
        entries = self._active_entries(payload)
        ctx = SharedContext(model=self.model, ttl=self.ttl, max_entries=self.max_entries)
        entry = ctx.put(key, content, agent=agent)
        entries[key] = {
            "key": entry.key,
            "agent": entry.agent,
            "original": entry.original,
            "compressed": entry.compressed,
            "original_tokens": entry.original_tokens,
            "compressed_tokens": entry.compressed_tokens,
            "savings_percent": entry.savings_percent,
            "timestamp": entry.timestamp,
            "transforms": entry.transforms,
        }
        if len(entries) > self.max_entries:
            overflow = len(entries) - self.max_entries
            for old_key, _ in sorted(entries.items(), key=lambda item: float(item[1].get("timestamp", 0)))[:overflow]:
                del entries[old_key]
        payload["entries"] = entries
        payload["model"] = self.model
        payload["ttl"] = self.ttl
        payload["max_entries"] = self.max_entries
        self._save(payload)
        return entries[key]

    def get(self, key: str, full: bool = False) -> str | None:
        payload = self._load()
        entries = self._active_entries(payload)
        self._save(payload)
        entry = entries.get(key)
        if not entry:
            return None
        return entry["original"] if full else entry["compressed"]

    def get_entry(self, key: str) -> dict[str, Any] | None:
        payload = self._load()
        entries = self._active_entries(payload)
        self._save(payload)
        return entries.get(key)

    def keys(self) -> list[str]:
        payload = self._load()
        entries = self._active_entries(payload)
        self._save(payload)
        return sorted(entries.keys())

    def stats(self) -> dict[str, Any]:
        payload = self._load()
        entries = self._active_entries(payload)
        self._save(payload)
        total_original = sum(int(entry.get("original_tokens", 0)) for entry in entries.values())
        total_compressed = sum(int(entry.get("compressed_tokens", 0)) for entry in entries.values())
        total_saved = total_original - total_compressed
        savings_percent = round((total_saved / total_original) * 100, 1) if total_original else 0.0
        return {
            "entries": len(entries),
            "keys": sorted(entries.keys()),
            "total_original_tokens": total_original,
            "total_compressed_tokens": total_compressed,
            "total_tokens_saved": total_saved,
            "savings_percent": savings_percent,
            "model": payload.get("model", self.model),
            "ttl": payload.get("ttl", self.ttl),
            "max_entries": payload.get("max_entries", self.max_entries),
        }

    def clear(self) -> dict[str, Any]:
        payload = {"model": self.model, "ttl": self.ttl, "max_entries": self.max_entries, "entries": {}}
        self._save(payload)
        return {"cleared": True}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Project-scoped Headroom SharedContext CLI")
    parser.add_argument("command", choices=["put", "get", "entry", "keys", "stats", "clear"])
    parser.add_argument("--key", default="")
    parser.add_argument("--text", default="")
    parser.add_argument("--file", default="")
    parser.add_argument("--agent", default="")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--store", default=str(default_store_path()))
    parser.add_argument("--model", default="claude-sonnet-4-5-20250929")
    parser.add_argument("--ttl", type=int, default=3600)
    parser.add_argument("--max-entries", type=int, default=100)
    return parser.parse_args()


def read_content(args: argparse.Namespace) -> str:
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.text:
        return args.text
    return sys.stdin.read()


def main() -> int:
    args = parse_args()
    ctx = ProjectSharedContext(Path(args.store), args.model, args.ttl, args.max_entries)
    if args.command == "put":
        if not args.key:
            raise SystemExit("--key required for put")
        content = read_content(args)
        if not content:
            raise SystemExit("content required for put")
        print(json.dumps(ctx.put(args.key, content, agent=args.agent or None), ensure_ascii=False, indent=2))
        return 0
    if args.command == "get":
        if not args.key:
            raise SystemExit("--key required for get")
        result = ctx.get(args.key, full=args.full)
        print("null" if result is None else result)
        return 0
    if args.command == "entry":
        if not args.key:
            raise SystemExit("--key required for entry")
        print(json.dumps(ctx.get_entry(args.key), ensure_ascii=False, indent=2))
        return 0
    if args.command == "keys":
        print(json.dumps(ctx.keys(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "stats":
        print(json.dumps(ctx.stats(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "clear":
        print(json.dumps(ctx.clear(), ensure_ascii=False, indent=2))
        return 0
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
