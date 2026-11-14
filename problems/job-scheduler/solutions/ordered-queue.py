from bisect import bisect_right, insort
from dataclasses import dataclass, field

QUEUED = "QUEUED"
RUNNING = "RUNNING"
DONE = "DONE"
FAILED = "FAILED"
CANCELLED = "CANCELLED"


@dataclass(slots=True)
class _Job:
    job_id: str
    tenant: str
    priority: int
    sequence: int
    depends_on: list[str]
    status: str = QUEUED
    not_before: int = 0
    failures: int = 0
    dependents: list[str] = field(default_factory=list)

    @property
    def order(self) -> tuple[int, int]:
        """Queue order: higher priority first, then earlier submission."""
        return -self.priority, self.sequence


@dataclass(frozen=True, slots=True)
class _RateLimit:
    limit: int
    window: int


@dataclass(frozen=True, slots=True)
class _RetryPolicy:
    max_retries: int = 0
    base_delay: int = 0

    def delay_after(self, failures: int) -> int | None:
        """The wait before the next start, or None when no retry is left."""
        if failures > self.max_retries:
            return None
        return self.base_delay * 2 ** (failures - 1)


class JobScheduler:
    def __init__(self) -> None:
        self._jobs: dict[str, _Job] = {}
        self._queue: list[_Job] = []  # every QUEUED job, sorted by `order`
        self._starts: dict[str, list[int]] = {}  # tenant -> start times, ascending
        self._limits: dict[str, _RateLimit] = {}
        self._policies: dict[str, _RetryPolicy] = {}

    # Level 1
    def submit(self, timestamp: int, job_id: str, tenant: str, priority: int) -> bool:
        return self.submit_after(timestamp, job_id, tenant, priority, [])

    def run_next(self, timestamp: int) -> str:
        for job in self._queue:
            if self._can_start(job, timestamp):
                self._unqueue(job)
                job.status = RUNNING
                self._starts.setdefault(job.tenant, []).append(timestamp)
                return job.job_id
        return ""

    def status(self, timestamp: int, job_id: str) -> str:
        job = self._jobs.get(job_id)
        return "" if job is None else job.status

    def queued(self, timestamp: int) -> int:
        return len(self._queue)

    # Level 2
    def set_rate_limit(self, timestamp: int, tenant: str, limit: int, window_ms: int) -> None:
        self._limits[tenant] = _RateLimit(limit, window_ms)

    # Level 3
    def set_retry_policy(self, timestamp: int, tenant: str, max_retries: int, base_delay_ms: int) -> None:
        self._policies[tenant] = _RetryPolicy(max_retries, base_delay_ms)

    def complete(self, timestamp: int, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None or job.status != RUNNING:
            return False
        job.status = DONE
        return True

    def fail(self, timestamp: int, job_id: str) -> int:
        job = self._jobs.get(job_id)
        if job is None or job.status != RUNNING:
            return -1
        job.failures += 1
        delay = self._policies.get(job.tenant, _RetryPolicy()).delay_after(job.failures)
        if delay is None:
            job.status = FAILED
            self._cancel_dependents(job)
            return 0
        job.not_before = timestamp + delay
        self._enqueue(job)
        return job.not_before

    # Level 4
    def submit_after(
        self, timestamp: int, job_id: str, tenant: str, priority: int, depends_on: list[str]
    ) -> bool:
        if job_id in self._jobs:
            return False
        for dependency in depends_on:
            found = self._jobs.get(dependency)
            if found is None or found.status in (FAILED, CANCELLED):
                return False
        job = _Job(job_id, tenant, priority, len(self._jobs), list(depends_on))
        self._jobs[job_id] = job
        for dependency in depends_on:
            self._jobs[dependency].dependents.append(job_id)
        self._enqueue(job)
        return True

    def cancel(self, timestamp: int, job_id: str) -> int:
        job = self._jobs.get(job_id)
        if job is None or job.status != QUEUED:
            return 0
        self._unqueue(job)
        job.status = CANCELLED
        return 1 + self._cancel_dependents(job)

    def _can_start(self, job: _Job, timestamp: int) -> bool:
        if job.not_before > timestamp:
            return False
        if any(self._jobs[dependency].status != DONE for dependency in job.depends_on):
            return False
        return self._within_limit(job.tenant, timestamp)

    def _within_limit(self, tenant: str, timestamp: int) -> bool:
        limit = self._limits.get(tenant)
        if limit is None:
            return True
        starts = self._starts.get(tenant, [])
        in_window = len(starts) - bisect_right(starts, timestamp - limit.window)
        return in_window < limit.limit

    def _cancel_dependents(self, job: _Job) -> int:
        """Cancel every queued job that waits, directly or not, on `job`; return how many."""
        cancelled = 0
        pending = list(job.dependents)
        while pending:
            dependent = self._jobs[pending.pop()]
            if dependent.status == QUEUED:
                self._unqueue(dependent)
                dependent.status = CANCELLED
                cancelled += 1
                pending.extend(dependent.dependents)
        return cancelled

    def _enqueue(self, job: _Job) -> None:
        job.status = QUEUED
        insort(self._queue, job, key=lambda queued: queued.order)

    def _unqueue(self, job: _Job) -> None:
        position = bisect_right(self._queue, job.order, key=lambda queued: queued.order)
        del self._queue[position - 1]
