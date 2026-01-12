"""Job representation for the queueing simulation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Population(Enum):
    """
    Scenario type for ING1 students.
    
    ATELIER: TP period - many students, frequent small submissions
    PROJET: Project period - groups, less frequent but heavier testsuites
    ING: ING students (frequent arrivals, short jobs) - for Channels & Dams
    PREPA: PREPA students (rare arrivals, long jobs) - for Channels & Dams
    """
    ATELIER = "ATELIER"  # TP: high frequency, short jobs
    PROJET = "PROJET"    # Project: low frequency, long testsuites
    ING = "ING"          # ING population for Channels & Dams
    PREPA = "PREPA"      # PREPA population for Channels & Dams


class JobStatus(Enum):
    """Status of a job in the system."""
    WAITING = "waiting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    BACKED_UP = "backed_up"


@dataclass
class Job:
    """
    Represents a job (push tag) submitted to the moulinette.
    
    Attributes:
        id: Unique identifier for the job
        arrival_time: Time when the job entered the system
        service_time: Time required to process this job
        population: ATELIER or PROJET scenario (different load profiles)
        
    Tracked timestamps:
        queue_entry_time: When the job entered the queue
        service_start_time: When processing started
        service_end_time: When processing finished
        departure_time: When the job left the system entirely
    """
    id: int
    arrival_time: float
    service_time: float
    population: Population = Population.ATELIER
    
    # Tracking timestamps (set during simulation)
    queue_entry_time: Optional[float] = None
    service_start_time: Optional[float] = None
    service_end_time: Optional[float] = None
    departure_time: Optional[float] = None
    status: JobStatus = JobStatus.WAITING
    
    # For tandem queues (Waterfall)
    stage: int = 1
    backed_up: bool = False
    
    @property
    def waiting_time(self) -> Optional[float]:
        """Time spent waiting in queue before service."""
        if self.service_start_time is not None and self.queue_entry_time is not None:
            return self.service_start_time - self.queue_entry_time
        return None
    
    @property
    def sojourn_time(self) -> Optional[float]:
        """Total time in system (waiting + service)."""
        if self.departure_time is not None:
            return self.departure_time - self.arrival_time
        return None
    
    @property
    def response_time(self) -> Optional[float]:
        """Alias for sojourn_time (commonly used term)."""
        return self.sojourn_time
    
    def __repr__(self) -> str:
        return f"Job(id={self.id}, pop={self.population.value}, status={self.status.value})"
