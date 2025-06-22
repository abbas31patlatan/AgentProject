# File: action/swarm_orchestrator.py

"""Coordinate multiple AgentProject nodes in a swarm."""

from __future__ import annotations

import logging
from typing import Iterable

logger = logging.getLogger(__name__)


class SwarmOrchestrator:
    """Naive orchestrator broadcasting messages to remote peers."""

    def __init__(self, peers: Iterable[str] | None = None) -> None:
        self.peers = list(peers or [])

    def broadcast(self, message: str) -> None:
        """Log message to simulate network broadcast."""

        for peer in self.peers:
            logger.info("Sending to %s: %s", peer, message)

