#!/usr/bin/env python3
"""Safe, zero-dependency public HTTP/HTTPS fetch worker for GitHub Actions."""

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

GLOBAL_MAX_BYTES = 100 * 1024 * 1024
INLINE_TEXT_MAX = 64 * 1024
DEFAULT_MAX_BYTES = 8 * 1024 * 1024
DEFAULT_TTL = 24 * 60 * 60
MAX_REQUESTS = 32


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


def safe_name(value: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "._-" else "_" for c in value)
    return cleaned[:120] or "payload.bin"


def cache_paths(url: str) -> tuple[Path, Path]:
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return CACHE / f"{key}.bin", CACHE / f"{key}.json"


def load_cache(url: str, ttl: int) -> tuple[bytes, dict] | None:
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


def fetch_one(item: dict) -> dict:
    request_id = safe_name(str(item["id"]))
    url = str(item["url"])
    mode = item.get("mode", "binary")
    if mode not in {"binary", "text"}:
        raise ValueError("mode must be binary or text")

    max_bytes = int(item.get("max_bytes", DEFAULT_MAX_BYTES))
    max_bytes = max(1, min(max_bytes, GLOBAL_MAX_BYTES))
    ttl = max(0, int(item.get("cache_ttl_seconds", DEFAULT_TTL)))
    filename = safe_name(item.get("filename") or Path(urlparse(url).path).name or "payload.bin")

    validate_public_url(url)
    cached = load_cache(url, ttl) if ttl else None

    if cached:
        body, meta = cached
        from_cache = True
    else:
        req = Request(url, headers={"User-Agent": "GameAgentBridge/1.0", "Accept": "*/*"})
        with OPENER.open(req, timeout=20) as response:
            final_url = response.geturl()
            validate_public_url(final_url)
            chunks = []
            total = 0
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
    dest_dir = OUTBOX / run_id / request_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    dest.write_bytes(body)

    result = {
        "id": request_id,
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

    (dest_dir / "result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), "utf-8"
    )
    return result


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: fetch_worker.py path/to/queue.json", file=sys.stderr)
        return 2

    queue_path = Path(sys.argv[1])
    queue = json.loads(queue_path.read_text("utf-8"))
    items = queue.get("requests", [])
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_REQUESTS:
        raise ValueError(f"requests must contain 1..{MAX_REQUESTS} items")

    OUTBOX.mkdir(parents=True, exist_ok=True)
    RESPONSES.mkdir(parents=True, exist_ok=True)

    results = []
    for item in items:
        try:
            results.append(fetch_one(item))
        except Exception as exc:
            results.append({
                "id": safe_name(str(item.get("id", "unknown"))),
                "ok": False,
                "source_url": item.get("url"),
                "error": f"{type(exc).__name__}: {exc}",
            })

    document = {
        "version": 1,
        "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "generated_at_unix": int(time.time()),
        "artifact_name": f"game-agent-bridge-output-{os.environ.get('GITHUB_RUN_ID', 'local')}",
        "results": results,
    }
    (RESPONSES / "latest.json").write_text(
        json.dumps(document, indent=2, ensure_ascii=False), "utf-8"
    )

    failed = sum(not result["ok"] for result in results)
    print(json.dumps({"requests": len(results), "failed": failed}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
