import random

from src.core.customer import Customer, CustomerStatus
from src.core.event import Event, EventQueue, EventType
from src.core.queue import QueueSystem


class WaterfallSimulation:
    def __init__(
        self,
        arrival_rate: float,
        k_tests: int,
        mu_tests: float,
        cap_tests: int,
        mu_result: float,
        cap_result: int,
        verbose: bool = False,
    ):
        self.clock = 0.0
        self.event_queue = EventQueue()
        self.arrival_rate = arrival_rate
        self.verbose = verbose

        # Test-Suite Execution
        self.queue_test = QueueSystem("Tests", k_tests, mu_tests, cap_tests)

        # Result Sender
        self.queue_result = QueueSystem("Result", 1, mu_result, cap_result)

        self.customers: list[Customer] = []
        self.customer_id_counter = 0

    def _print(self, message: str):
        if self.verbose:
            print(message)

    def schedule_next_arrival(self):
        # Generate next arrival time
        inter_arrival = random.expovariate(
            self.arrival_rate
        )  # Time between arrivals follows Exponential distribution
        next_time = self.clock + inter_arrival
        self.event_queue.schedule_arrival(next_time, self.customer_id_counter)
        self._print(f"[T={self.clock:.2f}] Scheduled arrival for Customer {self.customer_id_counter} at T={next_time:.2f}")
        self.customer_id_counter += 1

    def run(self, duration: float):
        self._print(f"=== Starting simulation (duration={duration}) ===\n")
        # First arrival
        self.schedule_next_arrival()

        # Main loop
        while not self.event_queue.is_empty():  # While there are events to process
            event = self.event_queue.next_event()  # Get the next event
            self.clock = event.time  # Advance the clock

            if self.clock > duration:  # Stop condition
                break

            self.handle_event(event)  # Handle the event

        self._print(f"\n=== Simulation ended at T={self.clock:.2f} ===\n")

    def handle_event(self, event: Event):
        if event.event_type == EventType.ARRIVAL:
            self.handle_arrival(event)
        elif event.event_type == EventType.END_EXECUTION:
            self.handle_end_execution(event)
        elif event.event_type == EventType.END_RESULT:
            self.handle_end_result(event)

    def handle_arrival(self, event: Event):
        # Creation of the customer
        customer = Customer(event.customer_id, self.clock)
        self.customers.append(customer)  # Add to the list
        self._print(f"[T={self.clock:.2f}] Customer {customer.id} arrived")

        # Schedule the next arrival (to continue the chain)
        self.schedule_next_arrival()

        # Entry to the first queue system (Test suite)
        if self.queue_test.add_customer(customer):  # check if we can add the customer
            self._print(f"[T={self.clock:.2f}] Customer {customer.id} added to Tests queue")
            self.try_process_tests()  # Try to process tests immediately
        else:
            customer.status = CustomerStatus.REJECTED
            self._print(f"[T={self.clock:.2f}] Customer {customer.id} REJECTED (Tests queue full)")

    def try_process_tests(self):
        # While we can start services...
        while True:
            result = self.queue_test.start_service(self.clock)
            if not result:
                break  # No more free servers or no more customers

            server, customer, duration = result
            customer.status = CustomerStatus.BEING_PROCESSED
            customer.start_execution_time = self.clock
            customer.service_time_execution = duration
            self._print(f"[T={self.clock:.2f}] Customer {customer.id} started Tests execution (duration={duration:.2f})")

            # Schedule the END of the test
            self.event_queue.schedule_end_execution(
                self.clock + duration, customer.id, server.id
            )

    def handle_end_execution(self, event: Event):
        # Free the server in the Test suite queue
        customer = self.queue_test.end_service(event.server_id)
        if customer:
            customer.end_execution_time = self.clock
            self._print(f"[T={self.clock:.2f}] Customer {customer.id} finished Tests execution")

            # See if another customer was waiting for this server
            self.try_process_tests()

            # Move to the Result sending queue
            customer.status = CustomerStatus.WAITING_RESULT
            if self.queue_result.add_customer(customer):
                self._print(f"[T={self.clock:.2f}] Customer {customer.id} added to Result queue")
                self.try_process_result()
            else:
                # if cannot be added to the Result queue, reject
                customer.status = CustomerStatus.REJECTED
                self._print(f"[T={self.clock:.2f}] Customer {customer.id} REJECTED (Result queue full)")

    def try_process_result(self):
        # Process the Result sending queue
        while True:
            result = self.queue_result.start_service(self.clock)
            if not result:
                break

            server, customer, duration = result
            customer.start_result_time = self.clock
            customer.service_time_result = duration
            self._print(f"[T={self.clock:.2f}] Customer {customer.id} started Result sending (duration={duration:.2f})")

            self.event_queue.schedule_end_result(
                self.clock + duration, customer.id, server.id
            )

    def handle_end_result(self, event: Event):
        # Free the server in the Result sending queue
        customer = self.queue_result.end_service(event.server_id)
        if customer:
            customer.end_result_time = self.clock
            customer.status = CustomerStatus.COMPLETED
            self._print(f"[T={self.clock:.2f}] Customer {customer.id} COMPLETED")

            # See if another customer was waiting for this server
            self.try_process_result()

    def print_report(self):
        print(f"--- Simulation completed at T={self.clock:.2f} ---")
        completed = [c for c in self.customers if c.status == CustomerStatus.COMPLETED]
        rejected = [c for c in self.customers if c.status == CustomerStatus.REJECTED]
        in_progress = [
            c
            for c in self.customers
            if c.status in (CustomerStatus.WAITING_EXECUTION, CustomerStatus.BEING_PROCESSED, CustomerStatus.WAITING_RESULT)
        ]

        print(f"Total arrived: {len(self.customers)}")
        print(f"Successfully completed: {len(completed)}")
        
        print(f"Rejected: {len(rejected)}")
        if rejected:
            print(" Rejected Customer IDs:", [c.id for c in rejected])
        print(f"Still in progress: {len(in_progress)}")
        if in_progress:
            print(" In-progress Customer IDs:", [c.id for c in in_progress])

        print(f"Rejections (Tests): {self.queue_test.total_rejected}")
        print(f"Rejections (Result): {self.queue_result.total_rejected}")   

        if completed:
            sojourn_times = []
            waiting_times_exec = []
            waiting_times_result = []
            service_times_exec = []
            service_times_result = []

            for c in completed:
                if c.end_result_time and c.arrival_time:
                    sojourn_times.append(c.end_result_time - c.arrival_time)

                if c.start_execution_time and c.arrival_time:
                    waiting_times_exec.append(c.start_execution_time - c.arrival_time)

                if c.start_result_time and c.end_execution_time:
                    waiting_times_result.append(c.start_result_time - c.end_execution_time)

                if c.service_time_execution:
                    service_times_exec.append(c.service_time_execution)

                if c.service_time_result:
                    service_times_result.append(c.service_time_result)

            avg_sojourn = sum(sojourn_times) / len(sojourn_times)
            avg_wait_exec = sum(waiting_times_exec) / len(waiting_times_exec)
            avg_wait_result = sum(waiting_times_result) / len(waiting_times_result)
            avg_service_exec = sum(service_times_exec) / len(service_times_exec)
            avg_service_result = sum(service_times_result) / len(service_times_result)

            print("Completed customers:")
            print(f" Average sojourn time: {avg_sojourn:.2f}")
            print(f" Average waiting time (Tests): {avg_wait_exec:.2f}")
            print(f" Average waiting time (Result): {avg_wait_result:.2f}")
            print(f" Average service time (Tests): {avg_service_exec:.2f}")
            print(f" Average service time (Result): {avg_service_result:.2f}")
