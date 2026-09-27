#!/usr/bin/env python3
"""Build a compact derived state snapshot from GACP runtime files."""

from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
RUNTIME=HERE/"runtime"
CONFIG=json.loads((HERE/"config.json").read_text("utf-8"))

def load(path):
    try:return json.loads(Path(path).read_text("utf-8"))
    except Exception:return None
def parse_time(v):
    if not v:return None
    try:return datetime.fromisoformat(v.replace("Z","+00:00"))
    except ValueError:return None
def short_message(m):
    return {"message_id":m.get("message_id"),"from":m.get("from"),"to":m.get("to"),"type":m.get("type"),"created_at":m.get("created_at"),"thread_id":m.get("thread_id"),"reply_to":m.get("reply_to"),"requires_ack":m.get("requires_ack",False),"priority":m.get("priority","normal"),"body":str(m.get("body",""))[:500]}

def main():
    now=datetime.now(timezone.utc); stale_after=int(CONFIG["presence_stale_after_seconds"])
    agents=[]; agents_root=RUNTIME/"agents"
    if agents_root.exists():
        for d in sorted(p for p in agents_root.iterdir() if p.is_dir()):
            profile=load(d/"profile.json") or {}; presence=load(d/"presence.json") or {}; crypto=load(d/"crypto.json")
            last=parse_time(presence.get("last_seen_at")); stale=last is None or (now-last).total_seconds()>stale_after
            agents.append({"agent_id":profile.get("agent_id",d.name),"display_name":profile.get("display_name",d.name),"model":profile.get("model"),"status":presence.get("status","unknown"),"last_seen_at":presence.get("last_seen_at"),"stale":stale,"working_on":presence.get("working_on"),"work_branch":presence.get("work_branch"),"secure_chat_ready":bool(crypto)})
    rooms={}; rooms_root=RUNTIME/"chat"/"rooms"; limit=int(CONFIG["snapshot_room_message_limit"])
    if rooms_root.exists():
        for room in sorted(p for p in rooms_root.iterdir() if p.is_dir()):
            msgs=[]; md=room/"messages"
            if md.exists():
                for p in sorted(md.glob("*.json"),reverse=True)[:limit]:
                    d=load(p)
                    if d:msgs.append(short_message(d))
            rooms[room.name]=list(reversed(msgs))
    secure_rooms=[]
    sr=RUNTIME/"secure_rooms"
    if sr.exists():
        for rd in sorted(p for p in sr.iterdir() if p.is_dir()):
            m=load(rd/"manifest.json")
            if not m: continue
            md=rd/"messages"; files=sorted(md.glob("*.json")) if md.exists() else []
            secure_rooms.append({"room_id":m.get("room_id",rd.name),"owner_agent_id":m.get("owner_agent_id"),"epoch":m.get("epoch"),"members":[x.get("agent_id") for x in m.get("members",[])],"message_count":len(files),"latest_message_file":files[-1].name if files else None})
    locks=[]; lr=RUNTIME/"locks"
    if lr.exists():
        for p in sorted(lr.glob("*.json")):
            d=load(p)
            if not d:continue
            exp=parse_time(d.get("expires_at"))
            locks.append({"resource":d.get("resource"),"resource_slug":d.get("resource_slug",p.stem),"owner_agent_id":d.get("owner_agent_id"),"lease_id":d.get("lease_id"),"expires_at":d.get("expires_at"),"expired":exp is None or exp<=now,"generation":d.get("generation"),"purpose":d.get("purpose")})
    tasks=[]; tr=RUNTIME/"tasks"
    if tr.exists():
        for d in sorted(p for p in tr.iterdir() if p.is_dir()):
            task=load(d/"task.json")
            if not task:continue
            evdir=d/"events"; ev=[load(p) for p in sorted(evdir.glob("*.json"))] if evdir.exists() else []; ev=[x for x in ev if x]
            tasks.append({"task_id":task.get("task_id",d.name),"title":task.get("title"),"mode":task.get("mode"),"created_by":task.get("created_by"),"latest_event":ev[-1] if ev else None,"event_count":len(ev)})
    actions=[]; al=int(CONFIG["snapshot_action_limit"])
    if agents_root.exists():
        for p in sorted(agents_root.glob("*/actions/*.json"),reverse=True)[:al]:
            d=load(p)
            if d:actions.append({"event_id":d.get("event_id"),"agent_id":d.get("agent_id"),"timestamp":d.get("timestamp"),"kind":d.get("kind"),"status":d.get("status"),"summary":d.get("summary"),"refs":d.get("refs",[])})
    mailboxes={}; mr=RUNTIME/"mailboxes"
    if mr.exists():
        for d in sorted(p for p in mr.iterdir() if p.is_dir()):
            md=d/"messages"; mailboxes[d.name]=len(list(md.glob("*.json"))) if md.exists() else 0
    snapshot={"protocol_version":1,"generated_at":now.replace(microsecond=0).isoformat().replace("+00:00","Z"),"note":"Derived convenience view. Event, secure-room and lease files are authoritative.","agents":agents,"rooms":rooms,"secure_rooms":secure_rooms,"locks":locks,"tasks":tasks,"recent_actions":actions,"mailbox_message_counts":mailboxes}
    out=RUNTIME/"state"/"snapshot.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(snapshot,indent=2,ensure_ascii=False)+"\n","utf-8"); print(out); return 0
if __name__=="__main__": raise SystemExit(main())
