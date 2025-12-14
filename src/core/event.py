from dataclasses import dataclass, field
from enum import Enum
import heapq


class EventType(Enum):
    ARRIVAL = "arrival"  # Arrival of the student submission
    START_EXECUTION = "start_execution"  # Start of test-suite execution
    END_EXECUTION = "end_execution"  # End of test-suite execution
    START_RESULT = "start_result"  # Start of result sending
    END_RESULT = "end_result"  # End of result sending (student leaves the system)


@dataclass(order=True)  # Useful to easily compare events by time in the priority queue
class Event:
    time: float  # Time of the event
    event_type: EventType = field(compare=False)
    customer_id: int = field(default=None, compare=False)
    server_id: int = field(default=None, compare=False)

    def __repr__(self) -> str:
        return (
            f"Event(time={self.time:.3f}, type={self.event_type.value}, "
            f"customer={self.customer_id}, server={self.server_id})"
        )


class EventQueue:
    """
    Priority queue to manage events in the simulation.
    """

    def __init__(self):
        self._events: list[Event] = []
        self._event_count = 0

    def schedule(self, event: Event):
        """Adds an event to the queue."""
        heapq.heappush(self._events, event) # heappush uses the ordering defined in the Event dataclass 
        # So we have events ordered by time automatically
        # Head of the queue is the event with the smallest time
        self._event_count += 1

    def schedule_arrival(self, time: float, customer_id: int) -> Event:
        """Schedules an arrival event."""
        event = Event(time=time, event_type=EventType.ARRIVAL, customer_id=customer_id)
        self.schedule(event)
        return event

    def schedule_end_execution(
        self, time: float, customer_id: int, server_id: int
    ) -> Event:
        """Schedules an end of execution event."""
        event = Event(
            time=time,
            event_type=EventType.END_EXECUTION,
            customer_id=customer_id,
            server_id=server_id,
        )
        self.schedule(event)
        return event

    def schedule_end_result(
        self, time: float, customer_id: int, server_id: int
    ) -> Event:
        """Schedules an end of result event."""
        event = Event(
            time=time,
            event_type=EventType.END_RESULT,
            customer_id=customer_id,
            server_id=server_id,
        )
        self.schedule(event)
        return event

    def next_event(self) -> Event | None:
        if self._events:
            return heapq.heappop(self._events)
        return None

    def is_empty(self) -> bool:
        return len(self._events) == 0
