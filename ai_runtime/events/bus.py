from collections.abc import Callable
from typing import Any


class EventBus:

    def __init__(self):

        self._listeners: list[
            Callable[[Any], None]
        ] = []

    def subscribe(
        self,
        listener: Callable[[Any], None],
    ) -> None:

        self._listeners.append(listener)

    def unsubscribe(
        self,
        listener,
    ) -> None:

        self._listeners.remove(listener)

    def publish(
        self,
        event,
    ) -> None:

        for listener in list(self._listeners):

            listener(event)