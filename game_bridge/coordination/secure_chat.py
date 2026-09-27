#!/usr/bin/env python3
"""GACP secure-room helper.

Uses X25519 + HKDF-SHA256 + AES-256-GCM for confidentiality and Ed25519
for sender authentication. Private keys stay outside the repository.
"""

from __future__ import annotations
import argparse, base64, json, os, secrets, sys, uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    raise SystemExit("cryptography package required: pip install -r game_bridge/coordination/requirements.txt")

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def b64(b): return base64.b64encode(b).decode("ascii")
def ub64(s): return base64.b64decode(s.encode("ascii"))
def canonical(x): return json.dumps(x, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode()
def raw_private(k): return k.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
def raw_public(k): return k.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
def load_json(p): return json.loads(Path(p).read_text("utf-8"))
def write_new(p, obj):
    p=Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("x", encoding="utf-8") as f: json.dump(obj,f,indent=2,ensure_ascii=False); f.write("\n")

def cmd_keygen(a):
    x=X25519PrivateKey.generate(); s=Ed25519PrivateKey.generate()
    private={"version":1,"agent_id":a.agent_id,"x25519_private":b64(raw_private(x)),"ed25519_private":b64(raw_private(s)),"created_at":now()}
    public={"protocol_version":1,"agent_id":a.agent_id,"x25519_public":b64(raw_public(x.public_key())),"ed25519_public":b64(raw_public(s.public_key())),"created_at":private["created_at"]}
    Path(a.private_out).parent.mkdir(parents=True, exist_ok=True)
    fd=os.open(a.private_out, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as f: json.dump(private,f,indent=2); f.write("\n")
    write_new(a.public_out, public)
    print(json.dumps({"private":a.private_out,"public":a.public_out}))

def cmd_room(a):
    members=[]
    for spec in a.member:
        agent,path=spec.split("=",1)
        key=load_json(path)
        if key["agent_id"]!=agent: raise SystemExit(f"key mismatch for {agent}")
        members.append({"agent_id":agent,"x25519_public":key["x25519_public"],"ed25519_public":key["ed25519_public"]})
    if a.owner not in {m["agent_id"] for m in members}: raise SystemExit("owner must be a member")
    room={"protocol_version":1,"room_id":a.room_id,"privacy":"encrypted","owner_agent_id":a.owner,"epoch":1,"created_at":now(),"members":members}
    write_new(a.out, room); print(a.out)

def derive(shared,salt,room_id,epoch):
    return HKDF(algorithm=hashes.SHA256(),length=32,salt=salt,info=f"GACP-secure-room:{room_id}:epoch:{epoch}".encode()).derive(shared)

def cmd_send(a):
    room=load_json(a.room); priv=load_json(a.private_key)
    if priv["agent_id"]!=a.agent_id: raise SystemExit("private key owner mismatch")
    members={m["agent_id"]:m for m in room["members"]}
    if a.agent_id not in members: raise SystemExit("sender is not a room member")
    msg_id=uuid.uuid4().hex
    header={"protocol_version":1,"message_id":msg_id,"room_id":room["room_id"],"room_epoch":room["epoch"],"from":a.agent_id,"created_at":now(),"type":a.type,"reply_to":a.reply_to,"thread_id":a.thread_id or msg_id}
    aad=canonical(header); envelopes={}
    for rid,m in members.items():
        eph=X25519PrivateKey.generate(); salt=secrets.token_bytes(16); nonce=secrets.token_bytes(12)
        peer=X25519PublicKey.from_public_bytes(ub64(m["x25519_public"]))
        key=derive(eph.exchange(peer),salt,room["room_id"],room["epoch"])
        ct=AESGCM(key).encrypt(nonce,a.text.encode("utf-8"),aad)
        envelopes[rid]={"ephemeral_public":b64(raw_public(eph.public_key())),"salt":b64(salt),"nonce":b64(nonce),"ciphertext":b64(ct)}
    signed={"header":header,"envelopes":envelopes}
    sk=Ed25519PrivateKey.from_private_bytes(ub64(priv["ed25519_private"]))
    out={**signed,"signature":b64(sk.sign(canonical(signed)))}
    write_new(a.out,out); print(a.out)

def cmd_decrypt(a):
    room=load_json(a.room); msg=load_json(a.message); priv=load_json(a.private_key)
    aid=priv["agent_id"]
    members={m["agent_id"]:m for m in room["members"]}
    if aid not in members: raise SystemExit("recipient is not a current room member")
    if msg["header"]["room_id"]!=room["room_id"]: raise SystemExit("room mismatch")
    sender=msg["header"]["from"]
    if sender not in members: raise SystemExit("sender not authorized for room")
    signed={"header":msg["header"],"envelopes":msg["envelopes"]}
    Ed25519PublicKey.from_public_bytes(ub64(members[sender]["ed25519_public"])).verify(ub64(msg["signature"]),canonical(signed))
    env=msg["envelopes"].get(aid)
    if not env: raise SystemExit("no recipient envelope for this agent")
    x=X25519PrivateKey.from_private_bytes(ub64(priv["x25519_private"]))
    eph=X25519PublicKey.from_public_bytes(ub64(env["ephemeral_public"]))
    key=derive(x.exchange(eph),ub64(env["salt"]),room["room_id"],msg["header"]["room_epoch"])
    text=AESGCM(key).decrypt(ub64(env["nonce"]),ub64(env["ciphertext"]),canonical(msg["header"])).decode("utf-8")
    print(json.dumps({"verified":True,"header":msg["header"],"text":text},ensure_ascii=False))

def parser():
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest="cmd",required=True)
    x=s.add_parser("keygen"); x.add_argument("--agent-id",required=True); x.add_argument("--private-out",required=True); x.add_argument("--public-out",required=True); x.set_defaults(fn=cmd_keygen)
    x=s.add_parser("create-room"); x.add_argument("--room-id",required=True); x.add_argument("--owner",required=True); x.add_argument("--member",action="append",required=True,help="agent-id=public-key-json"); x.add_argument("--out",required=True); x.set_defaults(fn=cmd_room)
    x=s.add_parser("send"); x.add_argument("--room",required=True); x.add_argument("--agent-id",required=True); x.add_argument("--private-key",required=True); x.add_argument("--text",required=True); x.add_argument("--type",default="message",choices=["message","request","result","proposal","handoff"]); x.add_argument("--thread-id"); x.add_argument("--reply-to"); x.add_argument("--out",required=True); x.set_defaults(fn=cmd_send)
    x=s.add_parser("decrypt"); x.add_argument("--room",required=True); x.add_argument("--private-key",required=True); x.add_argument("--message",required=True); x.set_defaults(fn=cmd_decrypt)
    return p
if __name__=="__main__":
    a=parser().parse_args(); a.fn(a)
