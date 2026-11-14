type Status = "QUEUED" | "RUNNING" | "DONE" | "FAILED" | "CANCELLED";

class Job {
  readonly id: string;
  readonly tenant: string;
  readonly priority: number;
  readonly sequence: number;
  readonly dependsOn: readonly string[];
  readonly dependents: string[] = [];
  status: Status = "QUEUED";
  notBefore = 0;
  failures = 0;

  constructor(id: string, tenant: string, priority: number, sequence: number, dependsOn: readonly string[]) {
    this.id = id;
    this.tenant = tenant;
    this.priority = priority;
    this.sequence = sequence;
    this.dependsOn = dependsOn;
  }
}

interface RateLimit {
  readonly limit: number;
  readonly window: number;
}

interface RetryPolicy {
  readonly maxRetries: number;
  readonly baseDelay: number;
}

const NO_RETRIES: RetryPolicy = { maxRetries: 0, baseDelay: 0 };

// Queue order: higher priority first, then earlier submission.
function compareOrder(a: Job, b: Job): number {
  return b.priority - a.priority || a.sequence - b.sequence;
}

// The number of values in the ascending array `values` that are greater than `threshold`.
function countAbove(values: readonly number[], threshold: number): number {
  let low = 0;
  let high = values.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (values[middle] <= threshold) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }
  return values.length - low;
}

export class JobScheduler {
  private readonly jobs = new Map<string, Job>();
  private readonly queue: Job[] = []; // every QUEUED job, sorted by compareOrder
  private readonly starts = new Map<string, number[]>(); // tenant -> start times, ascending
  private readonly limits = new Map<string, RateLimit>();
  private readonly policies = new Map<string, RetryPolicy>();

  // Level 1
  submit(timestamp: number, jobId: string, tenant: string, priority: number): boolean {
    return this.submitAfter(timestamp, jobId, tenant, priority, []);
  }

  runNext(timestamp: number): string {
    const job = this.queue.find((candidate) => this.canStart(candidate, timestamp));
    if (job === undefined) {
      return "";
    }
    this.unqueue(job);
    job.status = "RUNNING";
    const tenantStarts = this.starts.get(job.tenant) ?? [];
    tenantStarts.push(timestamp);
    this.starts.set(job.tenant, tenantStarts);
    return job.id;
  }

  status(timestamp: number, jobId: string): string {
    return this.jobs.get(jobId)?.status ?? "";
  }

  queued(timestamp: number): number {
    return this.queue.length;
  }

  // Level 2
  setRateLimit(timestamp: number, tenant: string, limit: number, windowMs: number): void {
    this.limits.set(tenant, { limit, window: windowMs });
  }

  // Level 3
  setRetryPolicy(timestamp: number, tenant: string, maxRetries: number, baseDelayMs: number): void {
    this.policies.set(tenant, { maxRetries, baseDelay: baseDelayMs });
  }

  complete(timestamp: number, jobId: string): boolean {
    const job = this.jobs.get(jobId);
    if (job === undefined || job.status !== "RUNNING") {
      return false;
    }
    job.status = "DONE";
    return true;
  }

  fail(timestamp: number, jobId: string): number {
    const job = this.jobs.get(jobId);
    if (job === undefined || job.status !== "RUNNING") {
      return -1;
    }
    job.failures++;
    const policy = this.policies.get(job.tenant) ?? NO_RETRIES;
    if (job.failures > policy.maxRetries) {
      job.status = "FAILED";
      this.cancelDependents(job);
      return 0;
    }
    job.notBefore = timestamp + policy.baseDelay * 2 ** (job.failures - 1);
    this.enqueue(job);
    return job.notBefore;
  }

  // Level 4
  submitAfter(timestamp: number, jobId: string, tenant: string, priority: number, dependsOn: string[]): boolean {
    if (this.jobs.has(jobId)) {
      return false;
    }
    for (const dependency of dependsOn) {
      const status = this.jobs.get(dependency)?.status;
      if (status === undefined || status === "FAILED" || status === "CANCELLED") {
        return false;
      }
    }
    const job = new Job(jobId, tenant, priority, this.jobs.size, [...dependsOn]);
    this.jobs.set(jobId, job);
    for (const dependency of dependsOn) {
      this.jobs.get(dependency)?.dependents.push(jobId);
    }
    this.enqueue(job);
    return true;
  }

  cancel(timestamp: number, jobId: string): number {
    const job = this.jobs.get(jobId);
    if (job === undefined || job.status !== "QUEUED") {
      return 0;
    }
    this.unqueue(job);
    job.status = "CANCELLED";
    return 1 + this.cancelDependents(job);
  }

  private canStart(job: Job, timestamp: number): boolean {
    if (job.notBefore > timestamp) {
      return false;
    }
    if (job.dependsOn.some((dependency) => this.jobs.get(dependency)?.status !== "DONE")) {
      return false;
    }
    const limit = this.limits.get(job.tenant);
    if (limit === undefined) {
      return true;
    }
    return countAbove(this.starts.get(job.tenant) ?? [], timestamp - limit.window) < limit.limit;
  }

  // Cancel every queued job that waits, directly or not, on `job`; return how many.
  private cancelDependents(job: Job): number {
    let cancelled = 0;
    const pending = [...job.dependents];
    for (let id = pending.pop(); id !== undefined; id = pending.pop()) {
      const dependent = this.jobs.get(id);
      if (dependent !== undefined && dependent.status === "QUEUED") {
        this.unqueue(dependent);
        dependent.status = "CANCELLED";
        cancelled++;
        pending.push(...dependent.dependents);
      }
    }
    return cancelled;
  }

  private enqueue(job: Job): void {
    job.status = "QUEUED";
    this.queue.splice(this.position(job), 0, job);
  }

  private unqueue(job: Job): void {
    this.queue.splice(this.position(job) - 1, 1);
  }

  // The index of the first queued job that comes after `job` in queue order.
  private position(job: Job): number {
    let low = 0;
    let high = this.queue.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (compareOrder(this.queue[middle], job) <= 0) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    return low;
  }
}
