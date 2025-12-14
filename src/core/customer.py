from enum import Enum


class CustomerStatus(Enum):
    WAITING_EXECUTION = "waiting_execution"
    BEING_PROCESSED = "being_processed"
    WAITING_RESULT = "waiting_result"
    COMPLETED = "completed"
    REJECTED = "rejected"


class CustomerPopulation(Enum):
    ING = "ing"
    PREPA = "prepa"
    DEFAULT = "default"


class Customer:
    """
    A student submitting his code the moulinette.

    Attributes:
        id: Unique identifier
        arrival_time: Arrival time in the system
        population: Type of population (ING, PREPA, etc.)
        service_time_execution: Service time for the test-suite execution
        service_time_result: Service time for sending the result
        start_execution_time: Time when execution starts
        end_execution_time: Time when execution ends
        start_result_time: Time when sending the result starts
        end_result_time: Time when the customer leaves the system
        status: Current status of the customer
    """

    def __init__(
        self,
        id: int,
        arrival_time: float,
        population: CustomerPopulation = CustomerPopulation.DEFAULT,
        service_time_execution: float = None,
        service_time_result: float = None,
    ):
        self.id = id
        self.arrival_time = arrival_time
        self.population = population
        self.service_time_execution = service_time_execution
        self.service_time_result = service_time_result
        self.start_execution_time: float = None
        self.end_execution_time: float = None
        self.start_result_time: float = None
        self.end_result_time: float = None
        self.status: CustomerStatus = CustomerStatus.WAITING_EXECUTION

    def waiting_time_execution(self):
        """Waiting time before execution."""
        if self.start_execution_time is not None:
            return self.start_execution_time - self.arrival_time
        return None

    def waiting_time_result(self):
        """Waiting time before sending the result."""
        if self.start_result_time is not None and self.end_execution_time is not None:
            return self.start_result_time - self.end_execution_time
        return None

    def total_waiting_time(self):
        """Total waiting time."""
        w1 = self.waiting_time_execution()
        w2 = self.waiting_time_result()
        if w1 is not None and w2 is not None:
            return w1 + w2
        return None

    def sojourn_time(self):
        """Total time spent in the system."""
        if self.end_result_time is not None:
            return self.end_result_time - self.arrival_time
        return None

    def __repr__(self) -> str:
        return f"Customer(id={self.id}, arrival={self.arrival_time:.2f}, status={self.status.value})"
