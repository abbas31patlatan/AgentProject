# File: core/utils/security.py

"""Security helpers for hashing and token generation."""

from __future__ import annotations

import hashlib
import secrets


def sha256(data: bytes) -> str:
    """Return the SHA256 hex digest for *data*."""

    return hashlib.sha256(data).hexdigest()


def random_token(length: int = 32) -> str:
    """Generate a random hex token."""

    return secrets.token_hex(length)

