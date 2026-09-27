#!/usr/bin/env python3
"""Build a compact derived state snapshot from GACP runtime files."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "runtime"
CONFIG = json.loads((HERE / "config.json").read_text("utf-8"))


def load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception:
        return None


def parse_time(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def short_message(msg: dict) -> dict:
    body = str(msg.get("body", ""))
    return {
        "message_id": msg.get("message_id"),
        "from": msg.get("from"),
        "to": msg.get("to"),
        "type": msg.get("type"),
        "created_at": msg.get("created_at"),
        "thread_id": msg.get("thread_id"),
        "reply_to": msg.get("reply_to"),
        "requires_ack": msg.get("requires_ack", False),
        "priority": msg.get("priority", "normal"),
        "body": body[:500],
    }


def main() -> int:
    now = datetime.now(timezone.utc)
    stale_after = int(CONFIG["presence_stale_after_seconds"])

    agents = []
    agents_root = RUNTIME / "agents"
    if agents_root.exists():
        for d in sorted(p for p in agents_root.iterdir() if p.is_dir()):
            profile = load(d / "profile.json") or {}
            presence = load(d / "presence.json") or {}
            last = parse_time(presence.get("last_seen_at"))
            stale = last is None or (now - last).total_seconds() > stale_after
            agents.append({
                "agent_id": profile.get("agent_id", d.name),
                "display_name": profile.get("display_name", d.name),
                "model": profile.get("model"),
                "status": presence.get("status", "unknown"),
                "last_seen_at": presence.get("last_seen_at"),
                "stale": stale,
                "working_on": presence.get("working_on"),
                "work_branch": presence.get("work_branch"),
            })

    rooms = {}
    rooms_root = RUNTIME / "chat" / "rooms"
    limit = int(CONFIG["snapshot_room_message_limit"])
    if rooms_root.exists():
        for room in sorted(p for p in rooms_root.iterdir() if p.is_dir()):
            messages = []
            msg_dir = room / "messages"
            if msg_dir.exists():
                for path in sorted(msg_dir.glob("*.json"), reverse=True)[:limit]:
                    data = load(path)
                    if data:
                        messages.append(short_message(data))
            rooms[room.name] = list(reversed(messages))

    locks = []
    lock_root = RUNTIME / "locks"
    if lock_root.exists():
        for path in sorted(lock_root.glob("*.json")):
            data = load(path)
            if not data:
                continue
            expires = parse_time(data.get("expires_at"))
            locks.append({
                "resource": data.get("resource"),
                "resource_slug": data.get("resource_slug", path.stem),
                "owner_agent_id": data.get("owner_agent_id"),
                "lease_id": data.get("lease_id"),
                "expires_at": data.get("expires_at"),
                "expired": expires is None or expires <= now,
                "generation": data.get("generation"),
                "purpose": data.get("purpose"),
            })

    tasks = []
    task_root = RUNTIME / "tasks"
    if task_root.exists():
        for d in sorted(p for p in task_root.iterdir() if p.is_dir()):
            task = load(d / "task.json")
            if not task:
                continue
            events = []
            event_dir = d / "events"
            if event_dir.exists():
                for path in sorted(event_dir.glob("*.json")):
                    data = load(path)
                    if data:
                        events.append(data)
            latest = events[-1] if events else None
            tasks.append({
                "task_id": task.get("task_id", d.name),
                "title": task.get("title"),
                "mode": task.get("mode"),
                "created_by": task.get("created_by"),
                "latest_event": latest,
                "event_count": len(events),
            })

    actions = []
    action_limit = int(CONFIG["snapshot_action_limit"])
    if agents_root.exists():
        action_paths = sorted(agents_root.glob("*/actions/*.json"), reverse=True)[:action_limit]
        for path in action_paths:
            data = load(path)
            if data:
                actions.append({
                    "event_id": data.get("event_id"),
                    "agent_id": data.get("agent_id"),
                    "timestamp": data.get("timestamp"),
                    "kind": data.get("kind"),
                    "status": data.get("status"),
                    "summary": data.get("summary"),
                    "refs": data.get("refs", []),
                })

    mailboxes = {}
    mailbox_root = RUNTIME / "mailboxes"
    if mailbox_root.exists():
        for d in sorted(p for p in mailbox_root.iterdir() if p.is_dir()):
            msg_dir = d / "messages"
            mailboxes[d.name] = len(list(msg_dir.glob("*.json"))) if msg_dir.exists() else 0

    snapshot = {
        "protocol_version": 1,
        "generated_at": now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "note": "Derived convenience view. Event and lease files are authoritative.",
        "agents": agents,
        "rooms": rooms,
        "locks": locks,
        "tasks": tasks,
        "recent_actions": actions,
        "mailbox_message_counts": mailboxes,
    }

    out = RUNTIME / "state" / "snapshot.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
