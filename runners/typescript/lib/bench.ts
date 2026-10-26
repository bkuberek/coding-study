// Bench mode (docs/specs/runners.md#bench-mode).
//
// Per size, in request order: each target makes one check call through the test path (its output
// is reported for output targets), then warmup samples until the timings settle (or have taken
// the per-call budget in total), then the timed
// repetitions take turns across targets, then one memory call per target. Every call, or batch of
// calls, is announced with `bench_start` first, so the CLI can attribute a hang.
//
// A sample makes `calls` back-to-back calls, each on its own freshly decoded input. Decoding and
// `gc()` happen outside the timed region; results stay referenced until the sample ends.

import { describeThrown } from "./failures.ts";
import {
  loadTarget,
  measuredRun,
  prepareCall,
  runTestCase,
  type LoadedTarget,
} from "./execute.ts";
import type {
  BenchInput,
  BenchJob,
  BenchSettings,
  BenchTarget,
  EventWriter,
} from "./protocol.ts";

const MEMORY_METRIC = "heap_used_delta";
const CV_WINDOW = 5;
const NANOSECONDS_PER_MICROSECOND = 1000;

/** Present when Node runs with `--expose-gc`. */
const collect = (globalThis as { gc?: () => void }).gc ?? (() => {});

interface Sample {
  readonly wallNs: number;
  readonly cpuNs: number;
  readonly calls: number;
}

interface Running {
  readonly spec: BenchTarget;
  readonly loaded: LoadedTarget;
  calls: number;
}

export async function runBenchJob(
  job: BenchJob,
  events: EventWriter,
): Promise<void> {
  events.write({ event: "job_start", job_id: job.jobId });
  const running: Running[] = [];
  for (const spec of job.targets) {
    const loaded = await loadTarget(spec.job);
    if ("shape" in loaded) {
      running.push({ spec, loaded, calls: 1 });
    } else {
      events.write({
        event: "load_error",
        job_id: job.jobId,
        target_id: spec.targetId,
        error: loaded,
      });
    }
  }
  new Bench(job, events).run(running);
  events.write({ event: "job_end", job_id: job.jobId });
}

class Bench {
  readonly #job: BenchJob;
  readonly #settings: BenchSettings;
  readonly #events: EventWriter;

  constructor(job: BenchJob, events: EventWriter) {
    this.#job = job;
    this.#settings = job.settings;
    this.#events = events;
  }

  run(targets: readonly Running[]): void {
    let active = [...targets];
    for (const input of this.#job.inputs) {
      active = active.filter((target) => this.#warmUp(target, input));
      active = this.#repetitions(active, input);
      if (this.#settings.memory) {
        active = active.filter((target) => this.#memory(target, input));
      }
    }
  }

  /** The check call, then warmup samples; false once the target is dropped. */
  #warmUp(target: Running, input: BenchInput): boolean {
    this.#start(target, input);
    const check = measuredRun((stopwatch) =>
      runTestCase(target.loaded, input.testCase, stopwatch),
    );
    if (check.status.status !== "ok") {
      this.#write("bench_error", target, input, {
        ...check.status,
        duration_ns: check.durationNs,
      });
      return false;
    }
    if (target.spec.emitsOutput) {
      this.#write("bench_output", target, input, { output: check.status.output });
    }
    if (this.#overBudget(target, input, check.durationNs)) {
      return false;
    }
    target.calls = this.#batch(input, 1, check.durationNs);
    const runs = [check.durationNs];
    const warmupStarted = process.hrtime.bigint();
    while (!this.#settled(runs) && !this.#warmedFor(warmupStarted)) {
      const sample = this.#sample(target, input);
      if (sample === null || this.#overBudget(target, input, perCall(sample))) {
        return false;
      }
      runs.push(perCall(sample));
      target.calls = this.#batch(input, target.calls, sample.wallNs);
    }
    return true;
  }

  /** Warmup, decoding and collection included, has taken the per-call budget. */
  #warmedFor(started: bigint): boolean {
    return Number(process.hrtime.bigint() - started) >= this.#settings.budgetNs;
  }

  #repetitions(active: readonly Running[], input: BenchInput): Running[] {
    let remaining = [...active];
    for (let rep = 1; rep <= this.#settings.reps; rep++) {
      for (const target of [...remaining]) {
        const sample = this.#sample(target, input);
        if (sample === null || this.#overBudget(target, input, perCall(sample))) {
          remaining = remaining.filter((other) => other !== target);
          continue;
        }
        this.#write("bench_sample", target, input, {
          rep,
          wall_ns: sample.wallNs,
          cpu_ns: sample.cpuNs,
          calls: sample.calls,
        });
      }
    }
    return remaining;
  }

  /** `heapUsed` growth over one call from a post-`gc()` baseline; false when the call fails. */
  #memory(target: Running, input: BenchInput): boolean {
    this.#start(target, input);
    const call = this.#prepared(target, input);
    if (call === null) {
      return false;
    }
    collect();
    const baseline = process.memoryUsage().heapUsed;
    let result: unknown;
    try {
      result = call();
    } catch (thrown) {
      this.#failed(target, input, thrown, 0);
      return false;
    }
    const grown = process.memoryUsage().heapUsed - baseline;
    keepAlive(result);
    this.#write("bench_memory", target, input, {
      metric: MEMORY_METRIC,
      bytes: Math.max(0, grown),
    });
    return true;
  }

  #sample(target: Running, input: BenchInput): Sample | null {
    this.#start(target, input);
    const calls: (() => unknown)[] = [];
    for (let index = 0; index < target.calls; index++) {
      const call = this.#prepared(target, input);
      if (call === null) {
        return null;
      }
      calls.push(call);
    }
    collect();
    const results: unknown[] = [];
    const cpuStarted = process.cpuUsage();
    const started = process.hrtime.bigint();
    try {
      for (const call of calls) {
        results.push(call());
      }
    } catch (thrown) {
      this.#failed(target, input, thrown, Number(process.hrtime.bigint() - started));
      return null;
    }
    const wallNs = Number(process.hrtime.bigint() - started);
    const cpu = process.cpuUsage(cpuStarted);
    keepAlive(results);
    const cpuNs = (cpu.user + cpu.system) * NANOSECONDS_PER_MICROSECOND;
    return { wallNs, cpuNs, calls: calls.length };
  }

  #prepared(target: Running, input: BenchInput): (() => unknown) | null {
    try {
      return prepareCall(target.loaded, input.testCase);
    } catch (thrown) {
      this.#failed(target, input, thrown, 0);
      return null;
    }
  }

  #settled(runs: readonly number[]): boolean {
    const { min, max, cv } = this.#settings.warmup;
    if (runs.length >= max) {
      return true;
    }
    if (runs.length < min) {
      return false;
    }
    const latest = runs.slice(-CV_WINDOW);
    return latest.length > 1 && coefficientOfVariation(latest) <= cv;
  }

  #batch(input: BenchInput, calls: number, sampleNs: number): number {
    const minimum = this.#settings.minSampleNs;
    if (sampleNs >= minimum) {
      return calls;
    }
    const wanted = Math.ceil((calls * minimum) / Math.max(sampleNs, 1));
    return Math.max(calls, Math.min(wanted, input.maxBatch));
  }

  #overBudget(target: Running, input: BenchInput, perCallNs: number): boolean {
    if (perCallNs <= this.#settings.budgetNs) {
      return false;
    }
    this.#write("bench_budget_exceeded", target, input, { wall_ns: perCallNs });
    return true;
  }

  #failed(target: Running, input: BenchInput, thrown: unknown, durationNs: number): void {
    this.#write("bench_error", target, input, {
      status: "error",
      error: describeThrown(thrown),
      duration_ns: durationNs,
    });
  }

  #start(target: Running, input: BenchInput): void {
    this.#write("bench_start", target, input, {});
  }

  #write(
    event: string,
    target: Running,
    input: BenchInput,
    fields: Readonly<Record<string, unknown>>,
  ): void {
    this.#events.write({
      event,
      job_id: this.#job.jobId,
      target_id: target.spec.targetId,
      size: input.size,
      ...fields,
    });
  }
}

function perCall(sample: Sample): number {
  return Math.floor(sample.wallNs / sample.calls);
}

function coefficientOfVariation(values: readonly number[]): number {
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  if (mean === 0) {
    return 0;
  }
  const variance =
    values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length;
  return Math.sqrt(variance) / mean;
}

/** Keeps a value reachable until here, so it is measured and freed after the timed region. */
function keepAlive(value: unknown): void {
  if (value === keepAlive) {
    throw new Error("unreachable");
  }
}
