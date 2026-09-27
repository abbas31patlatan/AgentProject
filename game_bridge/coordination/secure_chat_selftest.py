#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys, tempfile

HERE = Path(__file__).resolve().parent
TOOL = HERE / "secure_chat.py"

def run(*args):
    return subprocess.check_output([sys.executable, str(TOOL), *args], text=True).strip()

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    a_priv, a_pub = root/"a.private.json", root/"a.crypto.json"
    b_priv, b_pub = root/"b.private.json", root/"b.crypto.json"
    run("keygen","--agent-id","gpt-a","--private-out",str(a_priv),"--public-out",str(a_pub))
    run("keygen","--agent-id","gpt-b","--private-out",str(b_priv),"--public-out",str(b_pub))
    room = root/"room.json"
    run("create-room","--room-id","test-room","--owner","gpt-a","--member",f"gpt-a={a_pub}","--member",f"gpt-b={b_pub}","--out",str(room))
    msg = root/"message.json"
    run("send","--room",str(room),"--agent-id","gpt-a","--private-key",str(a_priv),"--text","secret diplomacy","--type","proposal","--out",str(msg))
    out=json.loads(run("decrypt","--room",str(room),"--private-key",str(b_priv),"--message",str(msg)))
    assert out["verified"] is True and out["text"]=="secret diplomacy"
print("secure chat self-test OK")
