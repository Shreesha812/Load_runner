"""
In-memory cancellation registry.
Maps run_id -> asyncio.Event. Setting the event signals all workers to stop
gracefully after in-flight requests complete.
"""
from __future__ import annotations

import asyncio


class CancelRegistry:

    def __init__(self) -> None:
        self._events: dict[str, asyncio.Event] = {}

    def register(self, run_id: str) -> asyncio.Event:
        """Create and store a cancel event for a run. Call before starting."""
        event = asyncio.Event()
        self._events[run_id] = event
        return event

    def cancel(self, run_id: str) -> bool:
        """Signal cancellation. Returns True if the run was found."""
        event = self._events.get(run_id)
        if event:
            event.set()
            return True
        return False

    def is_cancelled(self, run_id: str) -> bool:
        event = self._events.get(run_id)
        return event is not None and event.is_set()

    def get(self, run_id: str) -> asyncio.Event | None:
        return self._events.get(run_id)

    def remove(self, run_id: str) -> None:
        self._events.pop(run_id, None)


# Singleton shared across the app
cancel_registry = CancelRegistry()
