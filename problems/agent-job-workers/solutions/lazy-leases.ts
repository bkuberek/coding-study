const OK = "ok";
const LOST = "lost";
const ERROR = "error";

// One job in the shared store: its lease, whether it is done, and the steps saved so far.
class Job {
  holder = "";
  leaseEnd = 0;
  done = false;
  outputs: string[] = [];
}

interface Scaling {
  minWorkers: number;
  maxWorkers: number;
  jobsPerWorker: number;
  upCooldown: number;
  downCooldown: number;
  alertBacklog: number;
  workers: number;
  lastChange: number | null;
}

// A token bucket that is brought up to date only when it is looked at.
class Bucket {
  readonly capacity: number;
  readonly refillPerSecond: number;
  tokens: number;
  last: number | null = null;

  constructor(capacity: number, refillPerSecond: number) {
    this.capacity = capacity;
    this.refillPerSecond = refillPerSecond;
    this.tokens = capacity;
  }

  hasToken(now: number): boolean {
    if (this.last !== null) {
      this.tokens = Math.min(this.capacity, this.tokens + this.refillPerSecond * (now - this.last));
    }
    this.last = now;
    return this.tokens >= 1;
  }
}

class Breaker {
  readonly threshold: number;
  readonly openSeconds: number;
  failures = 0;
  openedAt: number | null = null;

  constructor(threshold: number, openSeconds: number) {
    this.threshold = threshold;
    this.openSeconds = openSeconds;
  }

  state(now: number): string {
    if (this.openedAt === null) {
      return "closed";
    }
    return now < this.openedAt + this.openSeconds ? "open" : "half_open";
  }

  record(now: number, outcome: string): void {
    const was = this.state(now);
    if (outcome === OK) {
      this.failures = 0;
      this.openedAt = null;
    } else if (was === "half_open") {
      this.openedAt = now;
    } else {
      this.failures += 1;
      if (this.failures >= this.threshold) {
        this.openedAt = now;
      }
    }
  }
}

export class AgentJobWorkers {
  private readonly lease: number;
  private readonly jobs = new Map<string, Job>();
  private doneCount = 0;
  private scaling: Scaling | null = null;
  private readonly toolBuckets = new Map<string, Bucket>();
  private readonly tenantBuckets = new Map<string, Bucket>();
  private readonly breakers = new Map<string, Breaker>();
  private maxAttempts = 1;
  private baseDelay = 0;
  private maxDelay = 0;

  constructor(leaseSeconds: number) {
    this.lease = leaseSeconds;
  }

  // Level 1
  submit(jobId: string): string {
    if (this.jobs.has(jobId)) {
      return "duplicate";
    }
    this.jobs.set(jobId, new Job());
    return "queued";
  }

  claim(now: number, workerId: string): string {
    let freeId = "";
    for (const [jobId, job] of this.jobs) {
      if (this.active(job, now)) {
        if (job.holder === workerId) {
          return jobId;
        }
      } else if (!job.done && freeId === "") {
        freeId = jobId;
      }
    }
    const free = this.jobs.get(freeId);
    if (free !== undefined) {
      free.holder = workerId;
      free.leaseEnd = now + this.lease;
    }
    return freeId;
  }

  heartbeat(now: number, workerId: string, jobId: string): string {
    const job = this.held(now, workerId, jobId);
    if (job === null) {
      return LOST;
    }
    job.leaseEnd = now + this.lease;
    return OK;
  }

  complete(now: number, workerId: string, jobId: string): string {
    if (this.jobs.get(jobId)?.done === true) {
      return "already_done";
    }
    const job = this.held(now, workerId, jobId);
    if (job === null) {
      return LOST;
    }
    job.done = true;
    job.holder = "";
    this.doneCount += 1;
    return OK;
  }

  jobState(now: number, jobId: string): string {
    const job = this.jobs.get(jobId);
    if (job === undefined) {
      return "unknown";
    }
    if (job.done) {
      return "done";
    }
    return this.active(job, now) ? "leased" : "queued";
  }

  // Level 2
  checkpoint(now: number, workerId: string, jobId: string, step: number, output: string): string {
    const job = this.held(now, workerId, jobId);
    if (job === null) {
      return LOST;
    }
    const saved = job.outputs.length;
    if (step <= saved) {
      return "duplicate";
    }
    if (step > saved + 1) {
      return "gap";
    }
    job.outputs.push(output);
    job.leaseEnd = now + this.lease;
    return OK;
  }

  progress(jobId: string): string[] {
    return [...(this.jobs.get(jobId)?.outputs ?? [])];
  }

  // Level 3
  setScaling(
    minWorkers: number,
    maxWorkers: number,
    jobsPerWorker: number,
    upCooldown: number,
    downCooldown: number,
    alertBacklog: number,
  ): void {
    this.scaling = {
      minWorkers,
      maxWorkers,
      jobsPerWorker,
      upCooldown,
      downCooldown,
      alertBacklog,
      workers: minWorkers,
      lastChange: null,
    };
  }

  scale(now: number): string[] {
    const rule = this.scaling;
    if (rule === null) {
      return [];
    }
    const backlog = this.jobs.size - this.doneCount;
    const needed = Math.ceil(backlog / rule.jobsPerWorker);
    const desired = Math.min(Math.max(needed, rule.minWorkers), rule.maxWorkers);
    let decision: string;
    if (desired === rule.workers) {
      decision = "hold";
    } else {
      const goingUp = desired > rule.workers;
      const wait = goingUp ? rule.upCooldown : rule.downCooldown;
      if (rule.lastChange === null || now - rule.lastChange >= wait) {
        rule.workers = desired;
        rule.lastChange = now;
        decision = goingUp ? "up" : "down";
      } else {
        decision = "cooldown";
      }
    }
    const alert = backlog >= rule.alertBacklog ? "on" : "off";
    return [decision, String(rule.workers), String(desired), alert];
  }

  // Level 4
  setToolLimit(tool: string, capacity: number, refillPerSecond: number): void {
    this.toolBuckets.set(tool, new Bucket(capacity, refillPerSecond));
  }

  setTenantLimit(tenant: string, capacity: number, refillPerSecond: number): void {
    this.tenantBuckets.set(tenant, new Bucket(capacity, refillPerSecond));
  }

  setRetry(maxAttempts: number, baseDelay: number, maxDelay: number): void {
    this.maxAttempts = maxAttempts;
    this.baseDelay = baseDelay;
    this.maxDelay = maxDelay;
  }

  setBreaker(tool: string, failureThreshold: number, openSeconds: number): void {
    this.breakers.set(tool, new Breaker(failureThreshold, openSeconds));
  }

  call(now: number, tenant: string, tool: string, outcomes: string[]): string[] {
    const breaker = this.breakers.get(tool);
    const buckets: [Bucket, string][] = [];
    const tenantBucket = this.tenantBuckets.get(tenant);
    if (tenantBucket !== undefined) {
      buckets.push([tenantBucket, "tenant_limit"]);
    }
    const toolBucket = this.toolBuckets.get(tool);
    if (toolBucket !== undefined) {
      buckets.push([toolBucket, "tool_limit"]);
    }
    let at = now;
    let attempts = 0;
    for (;;) {
      if (breaker !== undefined && breaker.state(at) === "open") {
        return ["circuit_open", String(attempts), String(at)];
      }
      for (const [bucket, reason] of buckets) {
        if (!bucket.hasToken(at)) {
          return [reason, String(attempts), String(at)];
        }
      }
      for (const [bucket] of buckets) {
        bucket.tokens -= 1;
      }
      const outcome = outcomes[attempts];
      attempts += 1;
      breaker?.record(at, outcome);
      if (outcome !== ERROR) {
        return [OK, String(attempts), String(at)];
      }
      if (attempts === this.maxAttempts) {
        return ["retries_exhausted", String(attempts), String(at)];
      }
      at += Math.min(this.baseDelay * 2 ** (attempts - 1), this.maxDelay);
    }
  }

  breakerState(now: number, tool: string): string {
    return this.breakers.get(tool)?.state(now) ?? "none";
  }

  // A lease is active while `now` is before its end; at the end it is over.
  private active(job: Job, now: number): boolean {
    return job.holder !== "" && !job.done && now < job.leaseEnd;
  }

  // The job when `workerId` holds an active lease on it, else null.
  private held(now: number, workerId: string, jobId: string): Job | null {
    const job = this.jobs.get(jobId);
    if (job === undefined || job.holder !== workerId || !this.active(job, now)) {
      return null;
    }
    return job;
  }
}
