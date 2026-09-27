#!/usr/bin/env python3
"""Zero-dependency helper for generating GACP v1 coordination records locally."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
import sys
import uuid

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "runtime"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slug(value: str, limit: int = 64) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9._-]+", "-", value).strip("-._")
    return (value or "agent")[:limit]


def validate_agent_id(agent_id: str) -> None:
    if not ID_RE.fullmatch(agent_id):
        raise SystemExit("invalid agent id: use lowercase letters/numbers plus ._- (3..64 chars)")


def atomic_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        fd = path.open("xb")
    except FileExistsError:
        raise SystemExit(f"refusing to overwrite immutable record: {path}")
    with fd:
        fd.write(data)
    return path


def replace_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", "utf-8")
    temp.replace(path)
    return path


def event_name(agent_id: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{stamp}__{agent_id}__{uuid.uuid4().hex[:10]}.json"


def cmd_new_id(args: argparse.Namespace) -> None:
    model = slug(args.model, 20)
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    print(f"gpt-{model}-{date}-{secrets.token_hex(3)}")


def cmd_register(args: argparse.Namespace) -> None:
    validate_agent_id(args.agent_id)
    profile = {
        "protocol_version": 1,
        "agent_id": args.agent_id,
        "display_name": args.display_name or args.agent_id,
        "agent_kind": args.kind,
        "model": args.model,
        "created_at": now(),
        "capabilities": sorted(set(args.capability or [])),
        "notes": args.notes or "",
    }
    base = RUNTIME / "agents" / args.agent_id
    atomic_json(base / "profile.json", profile)
    replace_json(base / "presence.json", {
        "protocol_version": 1,
        "agent_id": args.agent_id,
        "status": "active",
        "last_seen_at": now(),
        "working_on": args.working_on or "registration",
        "work_branch": args.work_branch,
    })
    print(base)


def cmd_heartbeat(args: argparse.Namespace) -> None:
    validate_agent_id(args.agent_id)
    path = RUNTIME / "agents" / args.agent_id / "presence.json"
    current = json.loads(path.read_text("utf-8")) if path.exists() else {}
    current.update({
        "protocol_version": 1,
        "agent_id": args.agent_id,
        "status": args.status,
        "last_seen_at": now(),
        "working_on": args.working_on,
        "work_branch": args.work_branch or current.get("work_branch"),
    })
    replace_json(path, current)
    print(path)


def message_payload(args: argparse.Namespace, destination: str) -> dict:
    message_id = uuid.uuid4().hex
    return {
        "protocol_version": 1,
        "message_id": message_id,
        "from": args.agent_id,
        "to": destination,
        "type": args.type,
        "created_at": now(),
        "thread_id": args.thread_id or message_id,
        "reply_to": args.reply_to,
        "requires_ack": bool(args.requires_ack),
        "priority": args.priority,
        "body": args.text,
        "refs": args.ref or [],
    }


def cmd_say(args: argparse.Namespace) -> None:
    validate_agent_id(args.agent_id)
    room = slug(args.room)
    payload = message_payload(args, f"room:{room}")
    path = RUNTIME / "chat" / "rooms" / room / "messages" / event_name(args.agent_id)
    atomic_json(path, payload)
    print(path)


def cmd_dm(args: argparse.Namespace) -> None:
    validate_agent_id(args.agent_id)
    validate_agent_id(args.to)
    payload = message_payload(args, args.to)
    path = RUNTIME / "mailboxes" / args.to / "messages" / event_name(args.agent_id)
    atomic_json(path, payload)
    print(path)


def cmd_action(args: argparse.Namespace) -> None:
    validate_agent_id(args.agent_id)
    event_id = uuid.uuid4().hex
    payload = {
        "protocol_version": 1,
        "event_id": event_id,
        "agent_id": args.agent_id,
        "timestamp": now(),
        "kind": args.kind,
        "status": args.status,
        "scope": args.scope,
        "summary": args.summary,
        "correlation_id": args.correlation_id,
        "refs": args.ref or [],
        "details": {},
    }
    path = RUNTIME / "agents" / args.agent_id / "actions" / event_name(args.agent_id)
    atomic_json(path, payload)
    print(path)


def resource_slug(resource: str) -> str:
    readable = slug(resource, 48)
    digest = hashlib.sha256(resource.encode("utf-8")).hexdigest()[:10]
    return f"{readable}--{digest}"


def cmd_lock_template(args: argparse.Namespace) -> None:
    validate_agent_id(args.agent_id)
    acquired = datetime.now(timezone.utc).replace(microsecond=0)
    from datetime import timedelta
    expires = acquired + timedelta(seconds=args.seconds)
    payload = {
        "protocol_version": 1,
        "resource": args.resource,
        "resource_slug": resource_slug(args.resource),
        "lease_id": uuid.uuid4().hex,
        "owner_agent_id": args.agent_id,
        "acquired_at": acquired.isoformat().replace("+00:00", "Z"),
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
        "generation": 1,
        "purpose": args.purpose,
    }
    print(json.dumps({
        "path": f"game_bridge/coordination/runtime/locks/{payload['resource_slug']}.json",
        "payload": payload,
    }, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="GACP v1 coordination helper")
    sub = p.add_subparsers(dest="command", required=True)

    x = sub.add_parser("new-id")
    x.add_argument("--model", default="sol")
    x.set_defaults(func=cmd_new_id)

    x = sub.add_parser("register")
    x.add_argument("--agent-id", required=True)
    x.add_argument("--display-name")
    x.add_argument("--kind", default="chatgpt")
    x.add_argument("--model", default="unknown")
    x.add_argument("--capability", action="append")
    x.add_argument("--notes")
    x.add_argument("--working-on")
    x.add_argument("--work-branch")
    x.set_defaults(func=cmd_register)

    x = sub.add_parser("heartbeat")
    x.add_argument("--agent-id", required=True)
    x.add_argument("--status", choices=["active", "idle", "blocked", "offline"], default="active")
    x.add_argument("--working-on", default="")
    x.add_argument("--work-branch")
    x.set_defaults(func=cmd_heartbeat)

    def add_message_args(x):
        x.add_argument("--agent-id", required=True)
        x.add_argument("--text", required=True)
        x.add_argument("--type", choices=["message", "request", "result", "handoff", "notice", "proposal"], default="message")
        x.add_argument("--thread-id")
        x.add_argument("--reply-to")
        x.add_argument("--requires-ack", action="store_true")
        x.add_argument("--priority", choices=["low", "normal", "high", "urgent"], default="normal")
        x.add_argument("--ref", action="append")

    x = sub.add_parser("say")
    add_message_args(x)
    x.add_argument("--room", default="lobby")
    x.set_defaults(func=cmd_say)

    x = sub.add_parser("dm")
    add_message_args(x)
    x.add_argument("--to", required=True)
    x.set_defaults(func=cmd_dm)

    x = sub.add_parser("action")
    x.add_argument("--agent-id", required=True)
    x.add_argument("--kind", required=True)
    x.add_argument("--summary", required=True)
    x.add_argument("--status", choices=["started", "progress", "succeeded", "failed", "blocked", "cancelled"], default="succeeded")
    x.add_argument("--scope", default="repo")
    x.add_argument("--correlation-id")
    x.add_argument("--ref", action="append")
    x.set_defaults(func=cmd_action)

    x = sub.add_parser("lock-template")
    x.add_argument("--agent-id", required=True)
    x.add_argument("--resource", required=True)
    x.add_argument("--seconds", type=int, default=900)
    x.add_argument("--purpose", default="")
    x.set_defaults(func=cmd_lock_template)

    return p


def main() -> int:
    args = build_parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
