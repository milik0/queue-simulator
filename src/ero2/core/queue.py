"""Queue and Server components for the simulation."""

from dataclasses import dataclass, field
from typing import Optional, List, Callable
from enum import Enum
import simpy

from .job import Job, JobStatus


class QueueDiscipline(Enum):
    """Queue service discipline."""
    FIFO = "fifo"  # First In First Out
    SJF = "sjf"    # Shortest Job First
    PRIORITY = "priority"  # Priority based on population


@dataclass
class QueueStats:
    """Statistics for a queue at a point in time."""
    current_length: int = 0
    total_arrivals: int = 0
    total_departures: int = 0
    total_rejected: int = 0
    
    @property
    def rejection_rate(self) -> float:
        """Proportion of arrivals that were rejected."""
        if self.total_arrivals == 0:
            return 0.0
        return self.total_rejected / self.total_arrivals


class Queue:
    """
    A queue with finite capacity and configurable discipline.
    
    This is the core building block for all queueing models.
    
    Attributes:
        capacity: Maximum number of jobs that can wait (K in M/M/1/K)
        discipline: Service order (FIFO, SJF, etc.)
        name: Identifier for logging/metrics
    """
    
    def __init__(
        self,
        env: simpy.Environment,
        capacity: int = float('inf'),
        discipline: QueueDiscipline = QueueDiscipline.FIFO,
        name: str = "queue"
    ):
        self.env = env
        self.capacity = capacity
        self.discipline = discipline
        self.name = name
        
        # Internal queue storage
        self._queue: List[Job] = []
        
        # Statistics
        self.stats = QueueStats()
        
        # For tracking queue length over time
        self._length_history: List[tuple[float, int]] = []
    
    def __len__(self) -> int:
        return len(self._queue)
    
    @property
    def is_full(self) -> bool:
        """Check if queue has reached capacity."""
        return len(self._queue) >= self.capacity
    
    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0
    
    def enqueue(self, job: Job) -> bool:
        """
        Add a job to the queue.
        
        Returns:
            True if job was added, False if rejected (queue full)
        """
        self.stats.total_arrivals += 1
        
        if self.is_full:
            job.status = JobStatus.REJECTED
            self.stats.total_rejected += 1
            return False
        
        job.queue_entry_time = self.env.now
        job.status = JobStatus.WAITING
        
        if self.discipline == QueueDiscipline.SJF:
            # Insert in sorted order by service time
            inserted = False
            for i, queued_job in enumerate(self._queue):
                if job.service_time < queued_job.service_time:
                    self._queue.insert(i, job)
                    inserted = True
                    break
            if not inserted:
                self._queue.append(job)
        else:
            # FIFO: append to end
            self._queue.append(job)
        
        self._record_length()
        return True
    
    def dequeue(self) -> Optional[Job]:
        """
        Remove and return the next job to be served.
        
        Returns:
            The next job, or None if queue is empty
        """
        if self.is_empty:
            return None
        
        job = self._queue.pop(0)
        self.stats.total_departures += 1
        self._record_length()
        return job
    
    def peek(self) -> Optional[Job]:
        """Look at the next job without removing it."""
        if self.is_empty:
            return None
        return self._queue[0]
    
    def _record_length(self):
        """Record current queue length for statistics."""
        self._length_history.append((self.env.now, len(self._queue)))
    
    def get_length_history(self) -> List[tuple[float, int]]:
        """Get the complete queue length history."""
        return self._length_history.copy()
    
    @property
    def current_length(self) -> int:
        """Current number of jobs in queue."""
        return len(self._queue)


class Server:
    """
    A server that processes jobs from a queue.
    
    Attributes:
        service_rate: μ - average jobs processed per unit time
        name: Identifier for logging/metrics
    """
    
    def __init__(
        self,
        env: simpy.Environment,
        service_rate: float,
        name: str = "server"
    ):
        self.env = env
        self.service_rate = service_rate
        self.name = name
        
        # Server state
        self._busy = False
        self._current_job: Optional[Job] = None
        
        # Statistics
        self.total_jobs_processed = 0
        self.total_busy_time = 0.0
        self._busy_start_time: Optional[float] = None
        
        # History for utilization tracking
        self._utilization_history: List[tuple[float, bool]] = []
    
    @property
    def is_busy(self) -> bool:
        """Check if server is currently processing a job."""
        return self._busy
    
    @property
    def utilization(self) -> float:
        """Calculate server utilization (ρ = busy_time / total_time)."""
        if self.env.now == 0:
            return 0.0
        return self.total_busy_time / self.env.now
    
    def process(self, job: Job) -> simpy.Event:
        """
        Process a job. This is a SimPy generator.
        
        Args:
            job: The job to process
            
        Yields:
            SimPy timeout for the service time
        """
        # Start processing
        self._busy = True
        self._current_job = job
        self._busy_start_time = self.env.now
        job.service_start_time = self.env.now
        job.status = JobStatus.PROCESSING
        self._utilization_history.append((self.env.now, True))
        
        # Process for service_time
        yield self.env.timeout(job.service_time)
        
        # Finish processing
        job.service_end_time = self.env.now
        job.status = JobStatus.COMPLETED
        self._busy = False
        self._current_job = None
        
        # Update statistics
        self.total_jobs_processed += 1
        self.total_busy_time += job.service_time
        self._utilization_history.append((self.env.now, False))
    
    def get_utilization_history(self) -> List[tuple[float, bool]]:
        """Get server busy/idle history."""
        return self._utilization_history.copy()


class ServerPool:
    """
    A pool of K identical servers (for M/M/k models).
    
    Jobs are assigned to the first available server.
    """
    
    def __init__(
        self,
        env: simpy.Environment,
        num_servers: int,
        service_rate: float,
        name: str = "pool"
    ):
        self.env = env
        self.num_servers = num_servers
        self.service_rate = service_rate
        self.name = name
        
        # Create the servers
        self.servers = [
            Server(env, service_rate, f"{name}_{i}")
            for i in range(num_servers)
        ]
        
        # SimPy resource for managing server access
        self.resource = simpy.Resource(env, capacity=num_servers)
    
    @property
    def num_busy(self) -> int:
        """Number of currently busy servers."""
        return sum(1 for s in self.servers if s.is_busy)
    
    @property
    def num_idle(self) -> int:
        """Number of currently idle servers."""
        return self.num_servers - self.num_busy
    
    @property
    def utilization(self) -> float:
        """Average utilization across all servers."""
        if not self.servers:
            return 0.0
        return sum(s.utilization for s in self.servers) / len(self.servers)
    
    def get_idle_server(self) -> Optional[Server]:
        """Get an idle server, or None if all busy."""
        for server in self.servers:
            if not server.is_busy:
                return server
        return None
