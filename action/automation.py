# File: action/automation.py

"""High level automation helpers for AgentProject."""

from __future__ import annotations

import logging
from typing import Iterable

logger = logging.getLogger(__name__)


class AutomationPipeline:
    """Execute a sequence of callable actions sequentially."""

    def __init__(self, steps: Iterable[callable] | None = None) -> None:
        self.steps = list(steps or [])

    def add_step(self, func: callable) -> None:
        """Add a callable step to the pipeline."""

        self.steps.append(func)

    def run(self) -> None:
        """Run all steps catching and logging any exceptions."""

        for step in self.steps:
            try:
                step()
            except Exception as exc:  # pragma: no cover - safety log
                logger.error("Automation step failed: %s", exc)
