#!/usr/bin/env python3
"""Safe, zero-dependency public HTTP/HTTPS fetch worker.

Supports GACP agent-scoped immutable request files and the legacy queue.json format.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
from pathlib import Path
import socket
import sys
import time
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(".bridge-cache")
OUTBOX = ROOT / "outbox"
RESPONSES = ROOT / "responses"
AGENT_RESPONSES = RESPONSES / "agents"

GLOBAL_MAX_BYTES = 100 * 1024 * 1024
INLINE_TEXT_MAX = 64 * 1024
DEFAULT_MAX_BYTES = 8 * 1024 * 1024
DEFAULT_TTL = 24 * 60 * 60
MAX_REQUESTS = 32


def safe_id(value: str, limit: int = 120) -> str:
    cleaned = "".join(c if c.isalnum() or c in "._-" else "_" for c in value)
    return cleaned[:limit] or "unknown"


def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("only http/https URLs are allowed")
    if not parsed.hostname:
        raise ValueError("URL has no hostname")
    if parsed.username or parsed.password:
        raise ValueError("credentials in URLs are not allowed")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    infos = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    if not infos:
        raise ValueError("hostname did not resolve")
    for info in infos:
        addr = ipaddress.ip_address(info[4][0])
        if not addr.is_global:
            raise ValueError(f"non-public destination rejected: {addr}")


class SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = build_opener(SafeRedirectHandler())


def canonical_hash(document: dict) -> str:
    raw = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def cache_paths(url: str) -> tuple[Path, Path]:
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return CACHE / f"{key}.bin", CACHE / f"{key}.json"


def load_cache(url: str, ttl: int):
    body_path, meta_path = cache_paths(url)
    if not body_path.exists() or not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text("utf-8"))
    if time.time() - float(meta.get("stored_at", 0)) > ttl:
        return None
    return body_path.read_bytes(), meta


def save_cache(url: str, body: bytes, meta: dict) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    body_path, meta_path = cache_paths(url)
    body_path.write_bytes(body)
    meta = dict(meta)
    meta["stored_at"] = time.time()
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")


def fetch_one(item: dict, agent_id: str, request_id: str) -> dict:
    item_id = safe_id(str(item["id"]))
    url = str(item["url"])
    mode = item.get("mode", "binary")
    if mode not in {"binary", "text"}:
        raise ValueError("mode must be binary or text")

    max_bytes = max(1, min(int(item.get("max_bytes", DEFAULT_MAX_BYTES)), GLOBAL_MAX_BYTES))
    ttl = max(0, int(item.get("cache_ttl_seconds", DEFAULT_TTL)))
    filename = safe_id(item.get("filename") or Path(urlparse(url).path).name or "payload.bin")

    validate_public_url(url)
    cached = load_cache(url, ttl) if ttl else None

    if cached:
        body, meta = cached
        from_cache = True
    else:
        req = Request(url, headers={"User-Agent": "GameAgentBridge/2.0", "Accept": "*/*"})
        with OPENER.open(req, timeout=20) as response:
            final_url = response.geturl()
            validate_public_url(final_url)
            chunks, total = [], 0
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError(f"response exceeded max_bytes={max_bytes}")
                chunks.append(chunk)
            body = b"".join(chunks)
            meta = {
                "source_url": url,
                "final_url": final_url,
                "status": getattr(response, "status", 200),
                "content_type": response.headers.get("Content-Type", ""),
            }
        save_cache(url, body, meta)
        from_cache = False

    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    dest_dir = OUTBOX / run_id / agent_id / request_id / item_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    dest.write_bytes(body)

    result = {
        "id": item_id,
        "ok": True,
        "source_url": url,
        "final_url": meta.get("final_url", url),
        "status": meta.get("status", 200),
        "content_type": meta.get("content_type", ""),
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "cached": from_cache,
        "artifact_path": str(dest.relative_to(ROOT)),
    }
    if mode == "text" and len(body) <= INLINE_TEXT_MAX:
        result["inline_text"] = body.decode(item.get("encoding", "utf-8"), errors="replace")
    (dest_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), "utf-8")
    return result


def request_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        return sorted(p for p in target.rglob("*.json") if p.is_file())
    raise FileNotFoundError(target)


def response_path_for(document: dict, source: Path) -> tuple[str, str, Path, bool]:
    legacy = "agent_id" not in document
    agent_id = safe_id(str(document.get("agent_id", "legacy")))
    request_id = safe_id(str(document.get("request_id", source.stem)))
    return agent_id, request_id, AGENT_RESPONSES / agent_id / f"{request_id}.json", legacy


def process_document(source: Path) -> tuple[bool, dict | None]:
    document = json.loads(source.read_text("utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{source}: root must be object")

    agent_id, request_id, response_path, legacy = response_path_for(document, source)
    request_hash = canonical_hash(document)

    if response_path.exists():
        existing = json.loads(response_path.read_text("utf-8"))
        if existing.get("request_sha256") != request_hash:
            raise ValueError(f"{source}: immutable request_id reused with different contents")
        return False, existing

    items = document.get("requests", [])
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_REQUESTS:
        raise ValueError(f"{source}: requests must contain 1..{MAX_REQUESTS} items")

    results = []
    for item in items:
        try:
            results.append(fetch_one(item, agent_id, request_id))
        except Exception as exc:
            results.append({
                "id": safe_id(str(item.get("id", "unknown"))),
                "ok": False,
                "source_url": item.get("url"),
                "error": f"{type(exc).__name__}: {exc}",
            })

    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    response = {
        "protocol_version": 1,
        "agent_id": agent_id,
        "request_id": request_id,
        "request_sha256": request_hash,
        "source_request_path": str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else str(source),
        "run_id": run_id,
        "generated_at_unix": int(time.time()),
        "artifact_name": f"game-agent-bridge-output-{run_id}",
        "results": results,
    }
    response_path.parent.mkdir(parents=True, exist_ok=True)
    response_path.write_text(json.dumps(response, indent=2, ensure_ascii=False) + "\n", "utf-8")

    if legacy:
        (RESPONSES / "latest.json").write_text(json.dumps(response, indent=2, ensure_ascii=False) + "\n", "utf-8")

    return True, response


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: fetch_worker.py request.json|inbox-directory", file=sys.stderr)
        return 2

    target = Path(sys.argv[1])
    OUTBOX.mkdir(parents=True, exist_ok=True)
    AGENT_RESPONSES.mkdir(parents=True, exist_ok=True)

    processed = 0
    skipped = 0
    failed = 0
    errors = []

    for source in request_files(target):
        try:
            was_processed, response = process_document(source)
            if was_processed:
                processed += 1
                failed += sum(not r.get("ok", False) for r in response.get("results", []))
            else:
                skipped += 1
        except Exception as exc:
            failed += 1
            errors.append({"source": str(source), "error": f"{type(exc).__name__}: {exc}"})

    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    summary_dir = OUTBOX / run_id
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "run_id": run_id,
        "processed_documents": processed,
        "skipped_documents": skipped,
        "failed": failed,
        "errors": errors,
    }
    (summary_dir / "run-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(json.dumps(summary))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
