from queue import Queue
from threading import Lock
from uuid import UUID

from app.schemas.domain import ProcessingEvent
from app.schemas.domain import RunExecutionEvent


class EventSubscriber:
    def __init__(self) -> None:
        self.queue: Queue[ProcessingEvent] = Queue()


class InMemoryEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[UUID, set[EventSubscriber]] = {}
        self._lock = Lock()

    def subscribe(self, conversation_id: UUID) -> EventSubscriber:
        subscriber = EventSubscriber()
        with self._lock:
            self._subscribers.setdefault(conversation_id, set()).add(subscriber)
        return subscriber

    def unsubscribe(self, conversation_id: UUID, subscriber: EventSubscriber) -> None:
        with self._lock:
            subscribers = self._subscribers.get(conversation_id)
            if subscribers is None:
                return
            subscribers.discard(subscriber)
            if not subscribers:
                self._subscribers.pop(conversation_id, None)

    def publish(self, event: ProcessingEvent) -> None:
        with self._lock:
            subscribers = list(self._subscribers.get(event.conversation_id, set()))
        for subscriber in subscribers:
            subscriber.queue.put(event)


event_bus = InMemoryEventBus()


class RunExecutionSubscriber:
    def __init__(self) -> None:
        self.queue: Queue[RunExecutionEvent] = Queue()


class InMemoryRunExecutionBus:
    def __init__(self) -> None:
        self._subscribers: dict[UUID, set[RunExecutionSubscriber]] = {}
        self._lock = Lock()

    def subscribe(self, run_id: UUID) -> RunExecutionSubscriber:
        subscriber = RunExecutionSubscriber()
        with self._lock:
            self._subscribers.setdefault(run_id, set()).add(subscriber)
        return subscriber

    def unsubscribe(self, run_id: UUID, subscriber: RunExecutionSubscriber) -> None:
        with self._lock:
            subscribers = self._subscribers.get(run_id)
            if subscribers is None:
                return
            subscribers.discard(subscriber)
            if not subscribers:
                self._subscribers.pop(run_id, None)

    def publish(self, event: RunExecutionEvent) -> None:
        with self._lock:
            subscribers = list(self._subscribers.get(event.run_id, set()))
        for subscriber in subscribers:
            subscriber.queue.put(event)


run_execution_bus = InMemoryRunExecutionBus()
