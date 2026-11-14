from dataclasses import dataclass, field

OK = "ok"
LOST = "lost"
ERROR = "error"


@dataclass(slots=True)
class _Job:
    """One job in the shared store: its lease, whether it is done, and the steps saved so far."""

    holder: str = ""
    lease_end: int = 0
    done: bool = False
    outputs: list[str] = field(default_factory=list)


@dataclass(slots=True)
class _Scaling:
    min_workers: int
    max_workers: int
    jobs_per_worker: int
    up_cooldown: int
    down_cooldown: int
    alert_backlog: int
    workers: int
    last_change: int | None = None


@dataclass(slots=True)
class _Bucket:
    """A token bucket that is brought up to date only when it is looked at."""

    capacity: int
    refill_per_second: int
    tokens: int
    last: int | None = None

    def has_token(self, now: int) -> bool:
        if self.last is not None:
            gained = self.refill_per_second * (now - self.last)
            self.tokens = min(self.capacity, self.tokens + gained)
        self.last = now
        return self.tokens >= 1


@dataclass(slots=True)
class _Breaker:
    threshold: int
    open_seconds: int
    failures: int = 0
    opened_at: int | None = None

    def state(self, now: int) -> str:
        if self.opened_at is None:
            return "closed"
        return "open" if now < self.opened_at + self.open_seconds else "half_open"

    def record(self, now: int, outcome: str) -> None:
        was = self.state(now)
        if outcome == OK:
            self.failures = 0
            self.opened_at = None
        elif was == "half_open":
            self.opened_at = now
        else:
            self.failures += 1
            if self.failures >= self.threshold:
                self.opened_at = now


class AgentJobWorkers:
    def __init__(self, lease_seconds: int) -> None:
        self._lease = lease_seconds
        self._jobs: dict[str, _Job] = {}
        self._done = 0
        self._scaling: _Scaling | None = None
        self._tool_buckets: dict[str, _Bucket] = {}
        self._tenant_buckets: dict[str, _Bucket] = {}
        self._breakers: dict[str, _Breaker] = {}
        self._max_attempts = 1
        self._base_delay = 0
        self._max_delay = 0

    # Level 1
    def submit(self, job_id: str) -> str:
        if job_id in self._jobs:
            return "duplicate"
        self._jobs[job_id] = _Job()
        return "queued"

    def claim(self, now: int, worker_id: str) -> str:
        free_id = ""
        for job_id, job in self._jobs.items():
            if self._active(job, now):
                if job.holder == worker_id:
                    return job_id
            elif not job.done and free_id == "":
                free_id = job_id
        if free_id != "":
            job = self._jobs[free_id]
            job.holder = worker_id
            job.lease_end = now + self._lease
        return free_id

    def heartbeat(self, now: int, worker_id: str, job_id: str) -> str:
        job = self._held(now, worker_id, job_id)
        if job is None:
            return LOST
        job.lease_end = now + self._lease
        return OK

    def complete(self, now: int, worker_id: str, job_id: str) -> str:
        known = self._jobs.get(job_id)
        if known is not None and known.done:
            return "already_done"
        job = self._held(now, worker_id, job_id)
        if job is None:
            return LOST
        job.done = True
        job.holder = ""
        self._done += 1
        return OK

    def job_state(self, now: int, job_id: str) -> str:
        job = self._jobs.get(job_id)
        if job is None:
            return "unknown"
        if job.done:
            return "done"
        return "leased" if self._active(job, now) else "queued"

    # Level 2
    def checkpoint(self, now: int, worker_id: str, job_id: str, step: int, output: str) -> str:
        job = self._held(now, worker_id, job_id)
        if job is None:
            return LOST
        saved = len(job.outputs)
        if step <= saved:
            return "duplicate"
        if step > saved + 1:
            return "gap"
        job.outputs.append(output)
        job.lease_end = now + self._lease
        return OK

    def progress(self, job_id: str) -> list[str]:
        job = self._jobs.get(job_id)
        return list(job.outputs) if job is not None else []

    # Level 3
    def set_scaling(
        self,
        min_workers: int,
        max_workers: int,
        jobs_per_worker: int,
        up_cooldown: int,
        down_cooldown: int,
        alert_backlog: int,
    ) -> None:
        self._scaling = _Scaling(
            min_workers,
            max_workers,
            jobs_per_worker,
            up_cooldown,
            down_cooldown,
            alert_backlog,
            workers=min_workers,
        )

    def scale(self, now: int) -> list[str]:
        rule = self._scaling
        if rule is None:
            return []
        backlog = len(self._jobs) - self._done
        needed = -(-backlog // rule.jobs_per_worker)
        desired = min(max(needed, rule.min_workers), rule.max_workers)
        if desired == rule.workers:
            decision = "hold"
        else:
            going_up = desired > rule.workers
            wait = rule.up_cooldown if going_up else rule.down_cooldown
            if rule.last_change is None or now - rule.last_change >= wait:
                rule.workers = desired
                rule.last_change = now
                decision = "up" if going_up else "down"
            else:
                decision = "cooldown"
        alert = "on" if backlog >= rule.alert_backlog else "off"
        return [decision, str(rule.workers), str(desired), alert]

    # Level 4
    def set_tool_limit(self, tool: str, capacity: int, refill_per_second: int) -> None:
        self._tool_buckets[tool] = _Bucket(capacity, refill_per_second, capacity)

    def set_tenant_limit(self, tenant: str, capacity: int, refill_per_second: int) -> None:
        self._tenant_buckets[tenant] = _Bucket(capacity, refill_per_second, capacity)

    def set_retry(self, max_attempts: int, base_delay: int, max_delay: int) -> None:
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._max_delay = max_delay

    def set_breaker(self, tool: str, failure_threshold: int, open_seconds: int) -> None:
        self._breakers[tool] = _Breaker(failure_threshold, open_seconds)

    def call(self, now: int, tenant: str, tool: str, outcomes: list[str]) -> list[str]:
        breaker = self._breakers.get(tool)
        buckets = [
            (bucket, reason)
            for bucket, reason in (
                (self._tenant_buckets.get(tenant), "tenant_limit"),
                (self._tool_buckets.get(tool), "tool_limit"),
            )
            if bucket is not None
        ]
        at = now
        attempts = 0
        while True:
            if breaker is not None and breaker.state(at) == "open":
                return ["circuit_open", str(attempts), str(at)]
            for bucket, reason in buckets:
                if not bucket.has_token(at):
                    return [reason, str(attempts), str(at)]
            for bucket, _ in buckets:
                bucket.tokens -= 1
            outcome = outcomes[attempts]
            attempts += 1
            if breaker is not None:
                breaker.record(at, outcome)
            if outcome != ERROR:
                return [OK, str(attempts), str(at)]
            if attempts == self._max_attempts:
                return ["retries_exhausted", str(attempts), str(at)]
            at += min(self._base_delay * 2 ** (attempts - 1), self._max_delay)

    def breaker_state(self, now: int, tool: str) -> str:
        breaker = self._breakers.get(tool)
        return breaker.state(now) if breaker is not None else "none"

    def _active(self, job: _Job, now: int) -> bool:
        """A lease is active while `now` is before its end; at the end it is over."""
        return job.holder != "" and not job.done and now < job.lease_end

    def _held(self, now: int, worker_id: str, job_id: str) -> _Job | None:
        """The job when `worker_id` holds an active lease on it, else None."""
        job = self._jobs.get(job_id)
        if job is None or job.holder != worker_id or not self._active(job, now):
            return None
        return job
