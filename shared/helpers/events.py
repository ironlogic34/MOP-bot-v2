"""Small async event bus for internal module-to-module notifications.

Events are dispatched sequentially. Failures are isolated and logged.
This is not a durable job queue or a replacement for transactional writes.
"""
import inspect
import logging
from collections import defaultdict
from collections.abc import Callable

log = logging.getLogger("mop.events")

class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, name: str, callback: Callable) -> None:
        if callback not in self._subscribers[name]:
            self._subscribers[name].append(callback)

    def unsubscribe(self, name: str, callback: Callable) -> None:
        callbacks = self._subscribers.get(name, [])
        if callback in callbacks:
            callbacks.remove(callback)

    async def emit(self, name: str, **payload) -> int:
        completed = 0
        for callback in tuple(self._subscribers.get(name, ())):
            try:
                result = callback(**payload)
                if inspect.isawaitable(result):
                    await result
                completed += 1
            except Exception:
                log.exception("Event handler failed for %s", name)
        return completed

    def subscribers(self, name: str) -> int:
        """Return the number of registered handlers for an event."""
        return len(self._subscribers.get(name, ()))
