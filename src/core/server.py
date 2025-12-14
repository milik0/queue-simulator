from src.core.customer import Customer


class Server:
    """
    Represents a single server (agent) within a station.
    """

    def __init__(self, id: int):
        self.id = id
        self.current_customer: Customer | None = None
        self.busy_until: float = 0.0
        self.total_customers_served: int = 0
        self.total_busy_time: float = 0.0
        self._service_start_time: float = 0.0

    def is_busy(self, current_time: float) -> bool:
        return current_time < self.busy_until

    def is_free(self, current_time: float) -> bool:
        return not self.is_busy(current_time)

    def start_service(
        self, customer: Customer, current_time: float, duration: float
    ) -> float:
        self.current_customer = customer
        self._service_start_time = current_time
        self.busy_until = current_time + duration
        return self.busy_until

    def end_service(self) -> Customer | None:
        if self.current_customer is None:
            return None

        customer = self.current_customer
        service_duration = self.busy_until - self._service_start_time
        self.total_busy_time += service_duration
        self.total_customers_served += 1

        self.current_customer = None
        return customer

    def __repr__(self):
        status = "Busy" if self.current_customer else "Free"
        return f"[Server {self.id}: {status}]"


class ServerPool:
    """
    Manages a collection of Servers.
    """

    def __init__(self, num_servers: int):
        self.servers: list[Server] = [Server(id=i) for i in range(num_servers)]

    def get_free_server(self, current_time: float) -> Server | None:
        for server in self.servers:
            if server.is_free(current_time):
                return server
        return None

    def get_busy_servers_count(self, current_time: float) -> int:
        # Count the number of busy servers at the given time
        # if current_time is 0, count all busy servers
        return sum(1 for s in self.servers if s.is_busy(current_time))

    def count(self) -> int:
        return len(self.servers)
