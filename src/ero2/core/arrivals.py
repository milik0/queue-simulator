"""Arrival process generators for the simulation."""

from typing import Callable, Optional, Generator
from dataclasses import dataclass
import numpy as np
import simpy

from .job import Job, Population


class PoissonArrivals:
    """
    Homogeneous Poisson arrival process.
    
    Inter-arrival times are exponentially distributed with rate λ.
    This is the standard arrival process for M/M/k models.
    
    Attributes:
        arrival_rate: λ - average arrivals per unit time
        service_rate: μ - average service rate (for generating service times)
    """
    
    def __init__(
        self,
        env: simpy.Environment,
        arrival_rate: float,
        service_rate: float,
        population: Population = Population.ATELIER,
        rng: Optional[np.random.Generator] = None
    ):
        self.env = env
        self.arrival_rate = arrival_rate  # λ
        self.service_rate = service_rate  # μ
        self.population = population
        self.rng = rng or np.random.default_rng()
        
        self._job_counter = 0
    
    def generate(self) -> Generator[tuple[simpy.Event, Job], None, None]:
        """
        Generate jobs according to Poisson process.
        
        Yields:
            Tuple of (timeout event, Job)
        """
        while True:
            # Exponential inter-arrival time
            inter_arrival = self.rng.exponential(1.0 / self.arrival_rate)
            yield self.env.timeout(inter_arrival)
            
            # Create job with exponential service time
            service_time = self.rng.exponential(1.0 / self.service_rate)
            self._job_counter += 1
            
            job = Job(
                id=self._job_counter,
                arrival_time=self.env.now,
                service_time=service_time,
                population=self.population
            )
            
            yield job
    
    def __iter__(self):
        return self.generate()


class NonHomogeneousArrivals:
    """
    Non-homogeneous Poisson process with time-varying rate λ(t).
    
    Uses thinning algorithm for exact simulation.
    Useful for modeling deadline-driven behavior where activity
    increases towards the end of a period.
    
    Example λ(t) patterns:
    - Constant: λ(t) = λ₀
    - Linear increase: λ(t) = λ₀ + αt
    - Peak pattern: λ(t) = λ₀ + A*exp(-(t-t_peak)²/σ²)
    """
    
    def __init__(
        self,
        env: simpy.Environment,
        rate_function: Callable[[float], float],
        max_rate: float,
        service_rate: float,
        population: Population = Population.ATELIER,
        rng: Optional[np.random.Generator] = None
    ):
        """
        Args:
            rate_function: λ(t) function returning arrival rate at time t
            max_rate: Upper bound on λ(t) for thinning algorithm
            service_rate: μ for service time distribution
        """
        self.env = env
        self.rate_function = rate_function
        self.max_rate = max_rate
        self.service_rate = service_rate
        self.population = population
        self.rng = rng or np.random.default_rng()
        
        self._job_counter = 0
    
    def generate(self) -> Generator[tuple[simpy.Event, Job], None, None]:
        """
        Generate jobs using thinning algorithm.
        """
        while True:
            # Generate candidate arrival using max rate
            inter_arrival = self.rng.exponential(1.0 / self.max_rate)
            yield self.env.timeout(inter_arrival)
            
            # Accept with probability λ(t) / λ_max
            current_rate = self.rate_function(self.env.now)
            acceptance_prob = current_rate / self.max_rate
            
            if self.rng.random() < acceptance_prob:
                # Accept this arrival
                service_time = self.rng.exponential(1.0 / self.service_rate)
                self._job_counter += 1
                
                job = Job(
                    id=self._job_counter,
                    arrival_time=self.env.now,
                    service_time=service_time,
                    population=self.population
                )
                
                yield job


class BatchArrivals:
    """
    Batch arrival process (M^X/M/k model).
    
    Jobs arrive in groups (batches) where:
    - Batch arrivals follow a Poisson process with rate λ
    - Batch size X follows a specified distribution
    
    Useful for modeling group work where multiple students
    submit nearly simultaneously.
    """
    
    def __init__(
        self,
        env: simpy.Environment,
        arrival_rate: float,
        service_rate: float,
        batch_size_mean: float = 3.0,
        batch_size_max: int = 10,
        population: Population = Population.ATELIER,
        rng: Optional[np.random.Generator] = None
    ):
        """
        Args:
            arrival_rate: λ - rate of batch arrivals
            batch_size_mean: Average batch size
            batch_size_max: Maximum batch size
        """
        self.env = env
        self.arrival_rate = arrival_rate
        self.service_rate = service_rate
        self.batch_size_mean = batch_size_mean
        self.batch_size_max = batch_size_max
        self.population = population
        self.rng = rng or np.random.default_rng()
        
        self._job_counter = 0
    
    def _sample_batch_size(self) -> int:
        """Sample batch size from geometric distribution."""
        # Geometric distribution shifted by 1 (minimum batch size = 1)
        p = 1.0 / self.batch_size_mean
        size = min(
            self.rng.geometric(p),
            self.batch_size_max
        )
        return max(1, size)
    
    def generate(self) -> Generator[tuple[simpy.Event, list[Job]], None, None]:
        """
        Generate batches of jobs.
        
        Yields:
            Tuple of (timeout event, list of Jobs)
        """
        while True:
            # Wait for next batch arrival
            inter_arrival = self.rng.exponential(1.0 / self.arrival_rate)
            yield self.env.timeout(inter_arrival)
            
            # Generate batch
            batch_size = self._sample_batch_size()
            batch = []
            
            for _ in range(batch_size):
                service_time = self.rng.exponential(1.0 / self.service_rate)
                self._job_counter += 1
                
                job = Job(
                    id=self._job_counter,
                    arrival_time=self.env.now,
                    service_time=service_time,
                    population=self.population
                )
                batch.append(job)
            
            yield batch


# Pre-defined rate functions for common patterns
def constant_rate(base_rate: float) -> Callable[[float], float]:
    """Constant arrival rate."""
    return lambda t: base_rate


def linear_increase(base_rate: float, slope: float) -> Callable[[float], float]:
    """Linearly increasing arrival rate."""
    return lambda t: base_rate + slope * t


def deadline_peak(
    base_rate: float,
    peak_rate: float,
    peak_time: float,
    width: float
) -> Callable[[float], float]:
    """
    Gaussian peak around deadline time.
    
    Models the typical pattern where submissions spike near deadlines.
    From the data: peak at 20:00-21:00 reaching 40 pushes/min.
    """
    def rate(t: float) -> float:
        gaussian = np.exp(-((t - peak_time) ** 2) / (2 * width ** 2))
        return base_rate + (peak_rate - base_rate) * gaussian
    return rate


def daily_pattern(
    base_rate: float = 5.0,
    peak_rate: float = 40.0,
    peak_hour: float = 20.5,  # 20:30
    morning_start: float = 8.0,
    evening_end: float = 23.0
) -> Callable[[float], float]:
    """
    Realistic daily pattern based on observed data.
    
    - Low activity before morning_start
    - Moderate activity during day
    - Peak around peak_hour
    - Drop after evening_end
    """
    def rate(t: float) -> float:
        # Normalize to 24-hour cycle
        hour = t % 24
        
        if hour < morning_start or hour > evening_end:
            return base_rate * 0.1  # Very low at night
        
        # Gaussian peak
        peak_factor = np.exp(-((hour - peak_hour) ** 2) / (2 * 2.0 ** 2))
        return base_rate + (peak_rate - base_rate) * peak_factor
    
    return rate
