"""agent-job-workers promises that its hidden cases catch the classic mistakes of running agent work
as background jobs: a lease that ends one second late or never, a queue that loses its order or
hands a worker a second job, a heartbeat or a completion accepted from a worker whose lease is
over, progress kept by the worker instead of the job, checkpoints that skip the lease check or
overwrite a saved step, a controller that counts the wrong backlog, rounds the wrong way or keeps
its cooldowns wrongly, and a tool gateway whose buckets, retries or circuit breakers take tokens,
count failures or keep time wrongly. These tests replay every case against a model of the system
written from the statement, which must give every expected output, and against that model with
one mistake planted at a time, which some hidden case must fail. The model keeps its jobs in plain
dictionaries keyed by job id and a list in submission order, where the reference keeps one record
per job. A mistake that crashes fails its case, as a thrown exception does in the grader."""

import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0384-agent-job-workers"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

CHECKS = ("circuit_open", "tenant_limit", "tool_limit")


class Model:
    """The system as the statement words it. Each mistake below overrides one hook."""

    checks: tuple[str, ...] = CHECKS

    def __init__(self, lease_seconds: int) -> None:
        self.lease = lease_seconds
        self.order: list[str] = []
        self.holder: dict[str, str] = {}
        self.end: dict[str, int] = {}
        self.finished: set[str] = set()
        self.saved: dict[Any, list[str]] = {}
        self.rule: dict[str, int] | None = None
        self.workers = 0
        self.changed_at: int | None = None
        self.buckets: dict[tuple[str, str], dict[str, Any]] = {}
        self.breakers: dict[str, dict[str, Any]] = {}
        self.max_attempts, self.base_delay, self.max_delay = 1, 0, 0

    # --- level 1 hooks
    def active(self, job: str, now: int) -> bool:
        return job in self.holder and job not in self.finished and now < self.end[job]

    def renewed_end(self, job: str, now: int) -> int:
        return now + self.lease

    def owns(self, now: int, worker: str, job: str) -> bool:
        return self.holder.get(job) == worker and self.active(job, now)

    def held_by(self, now: int, worker: str) -> str | None:
        return next((job for job in self.order if self.owns(now, worker, job)), None)

    def claimable(self, now: int) -> list[str]:
        return [job for job in self.order if job not in self.finished and not self.active(job, now)]

    def already_holding(self, now: int, job: str) -> str:
        return job

    def is_duplicate(self, job: str) -> bool:
        return job in self.order

    def complete_steps(self, now: int, worker: str, job: str) -> str:
        if job in self.finished:
            return "already_done"
        if not self.owns(now, worker, job):
            return "lost"
        self.finished.add(job)
        self.holder.pop(job)
        return "ok"

    # --- level 2 hooks
    def progress_key(self, job: str, worker: str) -> Any:
        return job

    def new_lease(self, job: str) -> None:
        pass

    def checkpoint_steps(self, now: int, worker: str, job: str, step: int, output: str) -> str:
        if not self.owns(now, worker, job):
            return "lost"
        saved = self.saved.setdefault(self.progress_key(job, worker), [])
        if step <= len(saved):
            return "duplicate"
        if step > len(saved) + 1:
            return "gap"
        saved.append(output)
        self.end[job] = self.renewed_end(job, now)
        return "ok"

    # --- level 3 hooks
    def backlog(self, now: int) -> int:
        return len(self.order) - len(self.finished)

    def needed(self, backlog: int, per_worker: int) -> int:
        return math.ceil(backlog / per_worker)

    def clamp(self, needed: int, low: int, high: int) -> int:
        return min(max(needed, low), high)

    def wait_for(self, going_up: bool) -> int:
        assert self.rule is not None
        return self.rule["up"] if going_up else self.rule["down"]

    def may_change(self, now: int, wait: int) -> bool:
        return self.changed_at is None or now - self.changed_at >= wait

    def new_count(self, desired: int) -> int:
        return desired

    def evaluated(self, now: int) -> None:
        pass

    def alert(self, backlog: int) -> bool:
        assert self.rule is not None
        return backlog >= self.rule["alert"]

    # --- level 4 hooks
    def fresh_bucket(self, capacity: int, refill: int) -> dict[str, Any]:
        return {"capacity": capacity, "refill": refill, "tokens": capacity, "last": None}

    def refill(self, bucket: dict[str, Any], now: int) -> None:
        if bucket["last"] is not None:
            gained = bucket["refill"] * (now - bucket["last"])
            bucket["tokens"] = min(bucket["capacity"], bucket["tokens"] + gained)
        bucket["last"] = now

    def take(self, buckets: Sequence[dict[str, Any]], refused: bool) -> None:
        if not refused:
            for bucket in buckets:
                bucket["tokens"] -= 1

    def charges(self, attempt: int) -> bool:
        return True

    def delay(self, failed_attempts: int) -> int:
        return min(self.base_delay * 2 ** (failed_attempts - 1), self.max_delay)

    def state(self, breaker: dict[str, Any], now: int) -> str:
        if breaker["opened"] is None:
            return "closed"
        return "open" if now < breaker["opened"] + breaker["seconds"] else "half_open"

    def trips(self, failures: int, threshold: int) -> bool:
        return failures >= threshold

    def record(self, breaker: dict[str, Any], now: int, outcome: str, attempt: int) -> None:
        was = self.state(breaker, now)
        if outcome == "ok":
            breaker["failures"], breaker["opened"] = 0, None
        elif was == "half_open":
            breaker["opened"] = now
        else:
            breaker["failures"] += 1
            if self.trips(breaker["failures"], breaker["threshold"]):
                breaker["opened"] = now

    def refused(self, breaker: dict[str, Any] | None, reason: str, at: int) -> None:
        pass

    def refusal_row(self, reason: str, attempts: int, at: int, started: int) -> list[str]:
        return [reason, str(attempts), str(at)]

    def exhausted(self, attempts: int) -> bool:
        return attempts >= self.max_attempts

    # --- the methods
    def submit(self, job_id: str) -> str:
        if self.is_duplicate(job_id):
            return "duplicate"
        self.order.append(job_id)
        return "queued"

    def claim(self, now: int, worker_id: str) -> str:
        held = self.held_by(now, worker_id)
        if held is not None:
            return self.already_holding(now, held)
        free = self.claimable(now)
        if not free:
            return ""
        job = free[0]
        self.holder[job], self.end[job] = worker_id, now + self.lease
        self.new_lease(job)
        return job

    def heartbeat(self, now: int, worker_id: str, job_id: str) -> str:
        if not self.owns(now, worker_id, job_id):
            return "lost"
        self.end[job_id] = self.renewed_end(job_id, now)
        return "ok"

    def complete(self, now: int, worker_id: str, job_id: str) -> str:
        return self.complete_steps(now, worker_id, job_id)

    def job_state(self, now: int, job_id: str) -> str:
        if job_id not in self.order:
            return "unknown"
        if job_id in self.finished:
            return "done"
        return "leased" if self.active(job_id, now) else "queued"

    def checkpoint(self, now: int, worker_id: str, job_id: str, step: int, output: str) -> str:
        return self.checkpoint_steps(now, worker_id, job_id, step, output)

    def progress(self, job_id: str) -> list[str]:
        holder = self.holder.get(job_id, "")
        return list(self.saved.get(self.progress_key(job_id, holder), []))

    def set_scaling(self, low: int, high: int, per: int, up: int, down: int, alert: int) -> None:
        self.rule = {"low": low, "high": high, "per": per, "up": up, "down": down, "alert": alert}
        self.workers, self.changed_at = low, None

    def scale(self, now: int) -> list[str]:
        if self.rule is None:
            return []
        backlog = self.backlog(now)
        desired = self.clamp(
            self.needed(backlog, self.rule["per"]), self.rule["low"], self.rule["high"]
        )
        if desired == self.workers:
            decision = "hold"
        elif self.may_change(now, self.wait_for(desired > self.workers)):
            decision = "up" if desired > self.workers else "down"
            self.workers, self.changed_at = self.new_count(desired), now
        else:
            decision = "cooldown"
        self.evaluated(now)
        return [decision, str(self.workers), str(desired), "on" if self.alert(backlog) else "off"]

    def set_tool_limit(self, tool: str, capacity: int, refill: int) -> None:
        self.buckets[("tool", tool)] = self.fresh_bucket(capacity, refill)

    def set_tenant_limit(self, tenant: str, capacity: int, refill: int) -> None:
        self.buckets[("tenant", tenant)] = self.fresh_bucket(capacity, refill)

    def set_retry(self, max_attempts: int, base_delay: int, max_delay: int) -> None:
        self.max_attempts, self.base_delay, self.max_delay = max_attempts, base_delay, max_delay

    def set_breaker(self, tool: str, threshold: int, seconds: int) -> None:
        self.breakers[tool] = {"threshold": threshold, "seconds": seconds, "failures": 0}
        self.breakers[tool]["opened"] = None

    def call(self, now: int, tenant: str, tool: str, outcomes: list[str]) -> list[str]:
        breaker = self.breakers.get(tool)
        limits = {
            "tenant_limit": self.buckets.get(("tenant", tenant)),
            "tool_limit": self.buckets.get(("tool", tool)),
        }
        at, attempts = now, 0
        while True:
            reason, passed = "", []
            for check in self.checks:
                if check == "circuit_open":
                    if breaker is not None and self.state(breaker, at) == "open":
                        reason = check
                        break
                    continue
                bucket = limits[check]
                if bucket is None or not self.charges(attempts + 1):
                    continue
                self.refill(bucket, at)
                if bucket["tokens"] < 1:
                    reason = check
                    break
                passed.append(bucket)
            self.take(passed, refused=bool(reason))
            if reason:
                self.refused(breaker, reason, at)
                return self.refusal_row(reason, attempts, at, now)
            outcome = outcomes[attempts]
            attempts += 1
            if breaker is not None:
                self.record(breaker, at, outcome, attempts)
            if outcome == "ok":
                return ["ok", str(attempts), str(at)]
            if self.exhausted(attempts):
                return ["retries_exhausted", str(attempts), str(at)]
            at += self.delay(attempts)

    def breaker_state(self, now: int, tool: str) -> str:
        breaker = self.breakers.get(tool)
        return "none" if breaker is None else self.state(breaker, now)


# ---------------------------------------------------------------- level 1: leases and the queue
class LeaseActiveAtItsEnd(Model):
    """Keeps a lease active at the second it ends."""

    def active(self, job, now):
        return job in self.holder and job not in self.finished and now <= self.end[job]


class LeaseNeverEnds(Model):
    """Never lets a lease run out, so a job whose worker died is stuck."""

    def active(self, job, now):
        return job in self.holder and job not in self.finished


class ReturnedJobGoesToTheBack(Model):
    """Puts a job whose lease ran out behind the jobs submitted after it."""

    def claimable(self, now):
        free = super().claimable(now)
        return [job for job in free if job not in self.holder] + [
            job for job in free if job in self.holder
        ]


class NewestJobFirst(Model):
    """Hands out the most recently submitted job first."""

    def claimable(self, now):
        return list(reversed(super().claimable(now)))


class SecondClaimGetsAnotherJob(Model):
    """Gives a worker that holds a lease a second job."""

    def held_by(self, now, worker):
        return None


class SecondClaimRenewsTheLease(Model):
    """Renews the lease when a worker claims the job it already holds."""

    def already_holding(self, now, job):
        self.end[job] = now + self.lease
        return job


class HeartbeatAfterTheEndAccepted(Model):
    """Accepts a heartbeat from the last holder until another worker claims the job."""

    def heartbeat(self, now, worker_id, job_id):
        if self.holder.get(job_id) == worker_id and job_id not in self.finished:
            self.end[job_id] = self.renewed_end(job_id, now)
            return "ok"
        return "lost"


class HeartbeatFromAnyWorker(Model):
    """Renews an active lease for whichever worker sends the heartbeat."""

    def heartbeat(self, now, worker_id, job_id):
        if job_id not in self.order or not self.active(job_id, now):
            return "lost"
        self.end[job_id] = self.renewed_end(job_id, now)
        return "ok"


class HeartbeatExtendsTheOldEnd(Model):
    """Adds a lease to the old end instead of counting it from now."""

    def renewed_end(self, job, now):
        return self.end[job] + self.lease


class DoneJobCanBeSubmittedAgain(Model):
    """Queues a job again when its id is submitted after the job is done."""

    def submit(self, job_id):
        if job_id in self.finished:
            self.finished.discard(job_id)
            return "queued"
        return super().submit(job_id)


class LateCompletionIsLost(Model):
    """Checks the lease before the job's state, so a late worker hears `lost` for a done job."""

    def complete_steps(self, now, worker, job):
        if not self.owns(now, worker, job):
            return "lost"
        return super().complete_steps(now, worker, job)


class CompletionFromAnyWorker(Model):
    """Lets a worker whose lease ran out complete the job another worker now holds."""

    def complete_steps(self, now, worker, job):
        if job in self.finished:
            return "already_done"
        if self.holder.get(job) != worker:
            return "lost"
        self.finished.add(job)
        self.holder.pop(job)
        return "ok"


class CompletionKeepsTheLease(Model):
    """Leaves the worker holding the lease of the job it completed."""

    def active(self, job, now):
        return job in self.holder and now < self.end[job]

    def complete_steps(self, now, worker, job):
        if job in self.finished:
            return "already_done"
        if not self.owns(now, worker, job):
            return "lost"
        self.finished.add(job)
        return "ok"


# ---------------------------------------------------------------- level 2: progress in the store
class ProgressKeptByTheWorker(Model):
    """Keeps the saved steps per worker, so the next worker starts from nothing."""

    def progress_key(self, job, worker):
        return (job, worker)


class ProgressClearedOnANewLease(Model):
    """Starts a job's progress again whenever a worker claims it."""

    def new_lease(self, job):
        self.saved[job] = []


class CheckpointWithoutTheLease(Model):
    """Saves a step from any worker that ever held the job, active lease or not."""

    def checkpoint_steps(self, now, worker, job, step, output):
        if self.holder.get(job) != worker:
            return "lost"
        saved = self.saved.setdefault(job, [])
        if step <= len(saved):
            return "duplicate"
        if step > len(saved) + 1:
            return "gap"
        saved.append(output)
        self.end[job] = self.renewed_end(job, now)
        return "ok"


class DuplicateBeforeTheLease(Model):
    """Answers `duplicate` before it checks the lease."""

    def checkpoint_steps(self, now, worker, job, step, output):
        if step <= len(self.saved.get(job, [])):
            return "duplicate"
        return super().checkpoint_steps(now, worker, job, step, output)


class DuplicateOverwritesTheStep(Model):
    """Replaces the output of a step that was saved before."""

    def checkpoint_steps(self, now, worker, job, step, output):
        saved = self.saved.get(job, [])
        if self.owns(now, worker, job) and step <= len(saved):
            saved[step - 1] = output
            return "duplicate"
        return super().checkpoint_steps(now, worker, job, step, output)


class GapAppended(Model):
    """Saves a step that skips ahead as the next step."""

    def checkpoint_steps(self, now, worker, job, step, output):
        saved = self.saved.get(job, [])
        if self.owns(now, worker, job) and step > len(saved) + 1:
            step = len(saved) + 1
        return super().checkpoint_steps(now, worker, job, step, output)


class CheckpointDoesNotRenew(Model):
    """Saves the step but leaves the lease's end alone."""

    def checkpoint_steps(self, now, worker, job, step, output):
        end = self.end.get(job)
        status = super().checkpoint_steps(now, worker, job, step, output)
        if status == "ok" and end is not None:
            self.end[job] = end
        return status


class DuplicateRenews(Model):
    """Renews the lease on a duplicate or a gap as well."""

    def checkpoint_steps(self, now, worker, job, step, output):
        status = super().checkpoint_steps(now, worker, job, step, output)
        if status in ("duplicate", "gap"):
            self.end[job] = now + self.lease
        return status


# ---------------------------------------------------------------- level 3: the controller
class BacklogCountsOnlyWaitingJobs(Model):
    """Counts the jobs nobody holds, not the ones being worked on."""

    def backlog(self, now):
        return len(self.claimable(now))


class BacklogCountsDoneJobs(Model):
    """Counts every job ever submitted."""

    def backlog(self, now):
        return len(self.order)


class NeededRoundsDown(Model):
    """Divides the backlog with integer division, which rounds down."""

    def needed(self, backlog, per_worker):
        return backlog // per_worker


class NoUpperBound(Model):
    """Never caps the workers at the maximum."""

    def clamp(self, needed, low, high):
        return max(needed, low)


class NoLowerBound(Model):
    """Lets the workers fall below the minimum."""

    def clamp(self, needed, low, high):
        return min(needed, high)


class CooldownEndsOneLate(Model):
    """Allows a change only when strictly more than the cooldown has passed."""

    def may_change(self, now, wait):
        return self.changed_at is None or now - self.changed_at > wait


class FirstChangeWaits(Model):
    """Counts the first cooldown from time 0, as if a change happened then."""

    def may_change(self, now, wait):
        return now - (self.changed_at or 0) >= wait


class CooldownFromEveryEvaluation(Model):
    """Restarts the cooldown at every evaluation, not only at a change."""

    def evaluated(self, now):
        self.changed_at = now


class CooldownsSwapped(Model):
    """Waits the scale-down cooldown before going up, and the other way round."""

    def wait_for(self, going_up):
        return super().wait_for(not going_up)


class CooldownPerDirection(Model):
    """Counts each cooldown from the last change in its own direction only."""

    def set_scaling(self, low, high, per, up, down, alert):
        super().set_scaling(low, high, per, up, down, alert)
        self.last_by_direction: dict[bool, int] = {}

    def wait_for(self, going_up):
        self.direction = going_up
        return super().wait_for(going_up)

    def may_change(self, now, wait):
        last = self.last_by_direction.get(self.direction)
        allowed = last is None or now - last >= wait
        if allowed:
            self.last_by_direction[self.direction] = now
        return allowed


class ScaleDownOneAtATime(Model):
    """Removes one worker per change instead of going to the desired count."""

    def new_count(self, desired):
        return desired if desired > self.workers else self.workers - 1


class AlertStrictlyAbove(Model):
    """Raises the alert only above the threshold, not at it."""

    def alert(self, backlog):
        assert self.rule is not None
        return backlog > self.rule["alert"]


class AlertFromTheWorkers(Model):
    """Compares the backlog the workers can hold, not the backlog, with the threshold."""

    def alert(self, backlog):
        assert self.rule is not None
        return self.workers * self.rule["per"] >= self.rule["alert"]


# ---------------------------------------------------------------- level 4: the tool gateway
class BreakerAfterTheLimits(Model):
    """Asks the rate limits before the breaker."""

    checks = ("tenant_limit", "tool_limit", "circuit_open")


class ToolLimitBeforeTenantLimit(Model):
    """Asks the tool's limit before the tenant's."""

    checks = ("circuit_open", "tool_limit", "tenant_limit")


class RefusedAttemptKeepsItsTokens(Model):
    """Takes the tokens of the buckets that passed even when a later check refuses."""

    def take(self, buckets, refused):
        super().take(buckets, refused=False)


class BucketStartsEmpty(Model):
    """Starts a bucket with no tokens."""

    def fresh_bucket(self, capacity, refill):
        bucket = super().fresh_bucket(capacity, refill)
        bucket["tokens"] = 0
        return bucket


class RefillWithoutACap(Model):
    """Lets a bucket fill beyond its capacity."""

    def refill(self, bucket, now):
        if bucket["last"] is not None:
            bucket["tokens"] += bucket["refill"] * (now - bucket["last"])
        bucket["last"] = now


class RefillFromTheLastToken(Model):
    """Counts the refill from the last time a token was taken instead of the last look."""

    def fresh_bucket(self, capacity, refill):
        bucket = super().fresh_bucket(capacity, refill)
        bucket["seen"] = None
        return bucket

    def refill(self, bucket, now):
        if bucket["last"] is not None:
            gained = bucket["refill"] * (now - bucket["last"])
            bucket["tokens"] = min(bucket["capacity"], bucket["tokens"] + gained)
        bucket["seen"] = now

    def take(self, buckets, refused):
        super().take(buckets, refused)
        if not refused:
            for bucket in buckets:
                bucket["last"] = bucket["seen"]


class RetriesAreFree(Model):
    """Charges a token for the first attempt of a call only."""

    def charges(self, attempt):
        return attempt == 1


class BackoffWithoutACap(Model):
    """Doubles the wait without the maximum."""

    def delay(self, failed_attempts):
        return self.base_delay * 2 ** (failed_attempts - 1)


class BackoffStartsDoubled(Model):
    """Waits twice the base delay after the first failure."""

    def delay(self, failed_attempts):
        return min(self.base_delay * 2**failed_attempts, self.max_delay)


class BackoffGrowsLinearly(Model):
    """Waits base, 2 base, 3 base and so on."""

    def delay(self, failed_attempts):
        return min(self.base_delay * failed_attempts, self.max_delay)


class MaxAttemptsCountsRetries(Model):
    """Reads `maxAttempts` as the number of retries after the first attempt."""

    def exhausted(self, attempts):
        return attempts >= self.max_attempts + 1


class BreakerCountsEveryFailure(Model):
    """Counts failures over the tool's life instead of in a row."""

    def record(self, breaker, now, outcome, attempt):
        if outcome == "ok" and self.state(breaker, now) == "closed":
            return
        super().record(breaker, now, outcome, attempt)


class BreakerTripsOneLate(Model):
    """Opens only after one failure more than the threshold."""

    def trips(self, failures, threshold):
        return failures > threshold


class OpenAtItsEnd(Model):
    """Keeps the breaker open at the second its open time ends."""

    def state(self, breaker, now):
        if breaker["opened"] is None:
            return "closed"
        return "open" if now <= breaker["opened"] + breaker["seconds"] else "half_open"


class FailedTrialKeepsTheOldTimer(Model):
    """Does not reopen the breaker when a half-open trial fails, so it stays half-open."""

    def record(self, breaker, now, outcome, attempt):
        if outcome != "ok" and self.state(breaker, now) == "half_open":
            return
        super().record(breaker, now, outcome, attempt)


class FailedTrialNeedsTheThreshold(Model):
    """Treats a half-open breaker like a closed one, so one failed trial does not reopen it."""

    def record(self, breaker, now, outcome, attempt):
        if self.state(breaker, now) == "half_open":
            breaker["opened"] = None
            breaker["failures"] = 0
        super().record(breaker, now, outcome, attempt)


class SuccessfulTrialKeepsTheCount(Model):
    """Closes the breaker after a good trial without clearing its count of failures."""

    def record(self, breaker, now, outcome, attempt):
        if outcome == "ok":
            if self.state(breaker, now) == "half_open":
                breaker["opened"] = None
            else:
                breaker["failures"] = 0
            return
        super().record(breaker, now, outcome, attempt)


class RefusalRestartsTheOpenTime(Model):
    """Restarts the open time whenever the open breaker refuses an attempt."""

    def refused(self, breaker, reason, at):
        if breaker is not None and reason == "circuit_open":
            breaker["opened"] = at


class BreakerSeesFirstAttemptsOnly(Model):
    """Tells the breaker about the first attempt of each call only."""

    def record(self, breaker, now, outcome, attempt):
        if attempt == 1:
            super().record(breaker, now, outcome, attempt)


class RefusedRetryReportsExhausted(Model):
    """Reports a refused retry as `retries_exhausted`."""

    def refusal_row(self, reason, attempts, at, started):
        if attempts > 0:
            return ["retries_exhausted", str(attempts), str(at)]
        return super().refusal_row(reason, attempts, at, started)


class RefusalAtTheStartTime(Model):
    """Reports the time the call started instead of the time of the refused attempt."""

    def refusal_row(self, reason, attempts, at, started):
        return [reason, str(attempts), str(started)]


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type(*case["args"][0])
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, AttributeError, AssertionError):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_time_never_goes_back_and_outcomes_cover_every_attempt():
    """The constraints promise that `now` never decreases, that a call starts no earlier than the
    end of the call before it, and that `outcomes` has an entry for every allowed attempt."""
    for case in CASES:
        latest, max_attempts = 0, 1
        for op, arguments, got in zip(case["ops"], case["args"], case["expected"], strict=True):
            if op == "setRetry":
                max_attempts = arguments[0]
            if op in ("submit", "progress", "AgentJobWorkers") or op.startswith("set"):
                continue
            assert arguments[0] >= latest, (case["id"], op, arguments)
            latest = arguments[0]
            if op == "call":
                assert len(arguments[3]) >= max_attempts, (case["id"], arguments)
                latest = int(got[2])


def test_the_hidden_cases_reach_every_answer():
    seen: dict[str, set[str]] = {}
    for case in HIDDEN_CASES:
        for op, got in zip(case["ops"], case["expected"], strict=True):
            if op in ("call", "scale") and got:
                seen.setdefault(op, set()).add(got[0])
            elif isinstance(got, str) and op != "claim":
                seen.setdefault(op, set()).add(got)
    assert seen["submit"] == {"queued", "duplicate"}
    assert seen["heartbeat"] == {"ok", "lost"}
    assert seen["complete"] == {"ok", "lost", "already_done"}
    assert seen["jobState"] == {"queued", "leased", "done", "unknown"}
    assert seen["checkpoint"] == {"ok", "lost", "duplicate", "gap"}
    assert seen["scale"] == {"up", "down", "hold", "cooldown"}
    assert seen["call"] == {"ok", "retries_exhausted", *CHECKS}
    assert seen["breakerState"] == {"closed", "open", "half_open", "none"}
