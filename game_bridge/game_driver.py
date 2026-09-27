#!/usr/bin/env python3
"""Minimal launcher/validator for Game Agent Bridge profiles."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


REQUIRED_TOP_LEVEL = {
    "schema_version",
    "id",
    "display_name",
    "runtime",
    "observation",
    "control",
    "state",
    "playbook",
}


def expand(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(value))


def load_profile(path: str) -> tuple[Path, dict]:
    profile_path = Path(path).resolve()
    profile = json.loads(profile_path.read_text("utf-8"))
    missing = REQUIRED_TOP_LEVEL - profile.keys()
    if missing:
        raise ValueError("missing keys: " + ", ".join(sorted(missing)))
    if profile["schema_version"] != 1:
        raise ValueError("unsupported schema_version")
    return profile_path, profile


def validate(path: str) -> None:
    profile_path, p = load_profile(path)
    launch = p["runtime"].get("launch", {})
    argv = launch.get("argv", [])
    if not isinstance(argv, list) or not argv:
        raise ValueError("runtime.launch.argv must be a non-empty list")
    if p["control"].get("mode") not in {"mouse_keyboard", "adapter", "api", "hybrid"}:
        raise ValueError("unsupported control.mode")
    playbook = profile_path.parent / p["playbook"]
    if not playbook.exists():
        raise ValueError(f"playbook not found: {playbook}")
    print(f"OK: {p['id']} ({p['display_name']})")


def launch(path: str) -> None:
    _, p = load_profile(path)
    spec = p["runtime"]["launch"]
    env = os.environ.copy()
    env.update({k: expand(str(v)) for k, v in spec.get("env", {}).items()})
    argv = [expand(str(x)) for x in spec["argv"]]
    cwd = expand(spec.get("cwd", "."))
    subprocess.Popen(argv, cwd=cwd, env=env, start_new_session=True)
    print("launched:", p["id"])


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in {"validate", "launch"}:
        print("usage: game_driver.py validate|launch path/to/profile.json")
        return 2
    if sys.argv[1] == "validate":
        validate(sys.argv[2])
    else:
        launch(sys.argv[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
