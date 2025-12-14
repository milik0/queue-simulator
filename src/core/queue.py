from collections import deque
import random

from src.core.customer import Customer
from src.core.server import ServerPool, Server


class QueueSystem:
    """
    Represents a queueing system with multiple servers and a waiting queue.
    """
    
    def __init__(
        self, name: str, num_servers: int, service_rate: float, capacity: int = None
    ):
        self.name = name
        self.service_rate = service_rate
        self.capacity = capacity  # None = infini

        self.queue: deque[Customer] = deque()
        self.server_pool = ServerPool(num_servers)

        self.total_arrivals = 0
        self.total_rejected = 0

    def can_accept_customer(self) -> bool:
        if self.capacity is None:
            return True

        # Load = clients in queue + clients being served
        current_load = len(self.queue) + self.server_pool.get_busy_servers_count(0)
        return current_load < self.capacity

    def add_customer(self, customer: Customer) -> bool:
        self.total_arrivals += 1

        if self.can_accept_customer():
            self.queue.append(customer)
            return True
        else:
            self.total_rejected += 1
            return False

    def has_waiting_customers(self) -> bool:
        return len(self.queue) > 0

    def start_service(
        self, current_time: float
    ) -> tuple[Server, Customer, float] | None:
        # Checks if there are waiting customers
        if not self.has_waiting_customers():
            return None

        free_server = self.server_pool.get_free_server(current_time)

        if free_server:
            # Retrieve the customer at the front of the queue
            customer = self.queue.popleft()

            # Generate the service duration (Exponential distribution)
            duration = random.expovariate(self.service_rate)

            # Start the service on the free server
            free_server.start_service(customer, current_time, duration)

            return free_server, customer, duration

        return None

    def end_service(self, server_id: int) -> Customer | None:
        # Find the server by its ID
        target_server = next(
            (s for s in self.server_pool.servers if s.id == server_id), None
        )

        # End the service on this server
        if target_server:
            return target_server.end_service()

        return None

    def __repr__(self):
        cap_str = "Inf" if self.capacity is None else str(self.capacity)
        return f"System({self.name} | Queue: {len(self.queue)}/{cap_str} | Servers: {self.server_pool.count()})"
