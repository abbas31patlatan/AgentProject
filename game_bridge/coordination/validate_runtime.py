#!/usr/bin/env python3
"""Lightweight structural validation for GACP runtime records."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "runtime"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")


def read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text("utf-8"))
    except Exception as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be object")
    return data


def require(path: Path, data: dict, *keys: str) -> None:
    missing = [k for k in keys if k not in data]
    if missing:
        raise ValueError(f"{path}: missing {', '.join(missing)}")


def validate() -> list[str]:
    errors = []

    for path in RUNTIME.glob("agents/*/profile.json"):
        try:
            d = read(path)
            require(path, d, "protocol_version", "agent_id", "display_name", "created_at")
            if d["agent_id"] != path.parent.name or not ID_RE.fullmatch(d["agent_id"]):
                raise ValueError(f"{path}: agent id/path mismatch")
        except ValueError as exc:
            errors.append(str(exc))

    for path in RUNTIME.glob("agents/*/presence.json"):
        try:
            d = read(path)
            require(path, d, "protocol_version", "agent_id", "status", "last_seen_at")
            if d["agent_id"] != path.parent.name:
                raise ValueError(f"{path}: presence owner/path mismatch")
        except ValueError as exc:
            errors.append(str(exc))

    for path in RUNTIME.glob("agents/*/actions/*.json"):
        try:
            d = read(path)
            require(path, d, "protocol_version", "event_id", "agent_id", "timestamp", "kind", "status", "summary")
            if d["agent_id"] != path.parents[1].name:
                raise ValueError(f"{path}: action owner/path mismatch")
        except ValueError as exc:
            errors.append(str(exc))

    for path in list(RUNTIME.glob("chat/rooms/*/messages/*.json")) + list(RUNTIME.glob("mailboxes/*/messages/*.json")):
        try:
            d = read(path)
            require(path, d, "protocol_version", "message_id", "from", "to", "type", "created_at", "body")
        except ValueError as exc:
            errors.append(str(exc))

    for path in RUNTIME.glob("locks/*.json"):
        try:
            d = read(path)
            require(path, d, "protocol_version", "resource", "resource_slug", "lease_id", "owner_agent_id", "acquired_at", "expires_at", "generation")
            if d["generation"] < 1:
                raise ValueError(f"{path}: generation must be >= 1")
        except (ValueError, TypeError) as exc:
            errors.append(str(exc))

    for path in RUNTIME.glob("tasks/*/task.json"):
        try:
            d = read(path)
            require(path, d, "protocol_version", "task_id", "title", "mode", "created_by", "created_at")
            if d["task_id"] != path.parent.name:
                raise ValueError(f"{path}: task id/path mismatch")
        except ValueError as exc:
            errors.append(str(exc))

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"{len(errors)} coordination validation error(s)", file=sys.stderr)
        return 1
    print("coordination runtime OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
