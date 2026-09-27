#!/usr/bin/env python3
from pathlib import Path

from game_driver import validate


def main() -> int:
    root = Path(__file__).resolve().parent / "games"
    profiles = sorted(root.glob("*/profile.json"))
    checked = 0
    for profile in profiles:
        if profile.parent.name == "_template":
            continue
        validate(str(profile))
        checked += 1
    if checked == 0:
        raise SystemExit("no game profiles found")
    print(f"validated {checked} game profile(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
