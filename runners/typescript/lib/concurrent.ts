// Concurrent jobs in the async model (docs/specs/runners.md#concurrent-jobs): sequential cases,
// then stress runs whose workers are async functions on the runner's one event loop.
//
// Every stress run is independent: fresh decoding, a fresh instance, fresh probe sections and
// fresh PRNGs. Workers start together once a shared gate opens; between ops a worker yields with
// `yieldProbability`, 1 to `maxYields` macrotasks. The schedule depends only on the code and the
// seed, so a failing seed reproduces exactly.

import { OutputCapture } from "./capture.ts";
import { InvalidInput, InvalidOutput } from "./codec.ts";
import {
  type Constructor,
  decodeArguments,
  invalidInput,
  loadTarget,
  memberOf,
  serializeResult,
  watchInputs,
} from "./execute.ts";
import { describeThrown } from "./failures.ts";
import type {
  ConcurrentJob,
  ErrorInfo,
  EventWriter,
  MemberSpec,
  OperationCase,
  Script,
  StressCase,
} from "./protocol.ts";

const HARNESS_PREFIX = "@";
const PRNG_MULTIPLIER = 1000003;
const MAX_PAUSE = 1000;

export async function runConcurrentJob(
  job: ConcurrentJob,
  events: EventWriter,
): Promise<void> {
  events.write({ event: "job_start", job_id: job.jobId });
  const loaded = await loadTarget(job.design);
  if (!("shape" in loaded)) {
    events.write({ event: "load_error", job_id: job.jobId, error: loaded });
  } else if (loaded.shape === "class") {
    for (const testCase of job.cases) {
      const ids = { job_id: job.jobId, case_id: testCase.id };
      events.write({ event: "case_start", ...ids });
      const result =
        "seed" in testCase
          ? await runStress(loaded.target, job, testCase)
          : await runSequential(loaded.target, job, testCase);
      events.write({ event: "case_result", ...ids, ...result });
    }
  }
  events.write({ event: "job_end", job_id: job.jobId });
}

type Fields = Record<string, unknown>;

/** A sequential case: like a design case, but awaitable results are awaited. */
async function runSequential(
  Target: Constructor,
  job: ConcurrentJob,
  testCase: OperationCase,
): Promise<Fields> {
  const capture = new OutputCapture();
  capture.start();
  const stopwatch = { elapsed: 0n };
  let fields: Fields;
  try {
    fields = await sequentialFields(Target, job, testCase, stopwatch);
  } catch (error) {
    fields = failureFields(error, "sequential case");
  }
  const stdout = capture.stop();
  const measured = { ...fields, duration_ns: Number(stopwatch.elapsed) };
  return stdout === "" ? measured : { ...measured, stdout };
}

async function sequentialFields(
  Target: Constructor,
  job: ConcurrentJob,
  testCase: OperationCase,
  stopwatch: { elapsed: bigint },
): Promise<Fields> {
  let instance: object = {};
  const outputs: unknown[] = [];
  for (const [index, op] of testCase.ops.entries()) {
    const prepared = prepare(job, index, op, testCase.args[index] ?? []);
    if ("status" in prepared) {
      return { ...prepared, op_index: index, partial_output: [...outputs] };
    }
    const started = process.hrtime.bigint();
    let value: unknown;
    try {
      value =
        index === 0
          ? new Target(...prepared.args)
          : await callMethod(instance, prepared, job);
    } catch (error) {
      stopwatch.elapsed += process.hrtime.bigint() - started;
      return {
        ...failureFields(error, `op ${index} (${op})`),
        op_index: index,
        partial_output: [...outputs],
      };
    }
    stopwatch.elapsed += process.hrtime.bigint() - started;
    if (index === 0) {
      instance = value as object;
      outputs.push(null);
      continue;
    }
    try {
      outputs.push(serializeResult(prepared.member, value, prepared.args, prepared.watched));
    } catch (error) {
      return failureFields(error, `op ${index} (${op})`);
    }
  }
  return { status: "ok", output: outputs };
}

interface Prepared {
  readonly op: string;
  readonly member: MemberSpec;
  readonly args: unknown[];
  readonly watched: ReturnType<typeof watchInputs>;
  readonly methodName: string;
}

interface Harness {
  readonly op: string;
  readonly args: readonly unknown[];
}

type Step = Prepared | Harness;

/** Decodes one op's arguments; harness ops keep theirs as written. */
function prepare(
  job: ConcurrentJob,
  index: number,
  op: string,
  json: readonly unknown[],
): Prepared | { readonly status: "error"; readonly error: ErrorInfo } {
  try {
    const member = memberOf(job.design, index, op);
    const args = decodeArguments(member.params, json);
    const methodName = job.design.methods.get(op)?.memberName ?? "";
    return { op, member, args, watched: watchInputs(member, args), methodName };
  } catch (error) {
    const info =
      error instanceof InvalidInput ? invalidInput(error) : describeThrown(error);
    return { status: "error", error: info };
  }
}

async function callMethod(
  instance: object,
  prepared: Prepared,
  job: ConcurrentJob,
): Promise<unknown> {
  const method = (instance as Record<string, unknown>)[prepared.methodName];
  if (typeof method !== "function") {
    throw new TypeError(`${job.design.exportName} has no method "${prepared.methodName}"`);
  }
  const value: unknown = Reflect.apply(method, instance, prepared.args);
  return isThenable(value) ? await value : value;
}

function isThenable(value: unknown): value is PromiseLike<unknown> {
  return (
    (typeof value === "object" || typeof value === "function") &&
    value !== null &&
    typeof (value as { then?: unknown }).then === "function"
  );
}

function failureFields(error: unknown, where: string): Fields {
  if (error instanceof InvalidOutput) {
    return { status: "invalid_output", reason: `${where}: ${error.message}` };
  }
  return {
    status: "error",
    error: error instanceof InvalidInput ? invalidInput(error) : describeThrown(error),
  };
}

/** Where a stress run failed, reported with its `error` or `invalid_output`. */
class StressFailure extends Error {
  readonly fields: Fields;

  constructor(fields: Fields) {
    super(String(fields.status));
    this.fields = fields;
  }
}

class HarnessError extends Error {
  override readonly name = "HarnessError";
}

/** Probe sections: entries, violations and the most workers inside at once. */
class Sections {
  readonly #counters = new Map<
    string,
    { shared: number; exclusive: number; entries: number; violations: number; max: number }
  >();

  enter(name: string, mode: string): void {
    const section = this.#counters.get(name) ?? {
      shared: 0,
      exclusive: 0,
      entries: 0,
      violations: 0,
      max: 0,
    };
    this.#counters.set(name, section);
    if (mode === "exclusive") {
      section.violations += section.shared + section.exclusive > 0 ? 1 : 0;
      section.exclusive += 1;
    } else {
      section.violations += section.exclusive > 0 ? 1 : 0;
      section.shared += 1;
    }
    section.entries += 1;
    section.max = Math.max(section.max, section.shared + section.exclusive);
  }

  exit(name: string, mode: string): void {
    const section = this.#counters.get(name);
    if (section !== undefined) {
      if (mode === "exclusive") {
        section.exclusive -= 1;
      } else {
        section.shared -= 1;
      }
    }
  }

  snapshot(): Fields {
    return Object.fromEntries(
      [...this.#counters].map(([name, section]) => [
        name,
        { entries: section.entries, violations: section.violations, max_occupancy: section.max },
      ]),
    );
  }
}

/** mulberry32: a small seeded PRNG; one stream per worker. */
function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) | 0;
    let value = Math.imul(state ^ (state >>> 15), 1 | state);
    value = (value + Math.imul(value ^ (value >>> 7), 61 | value)) ^ value;
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function macrotask(): Promise<void> {
  return new Promise((resolve) => setImmediate(resolve));
}

async function yieldTimes(count: number): Promise<void> {
  for (let index = 0; index < count; index++) {
    await macrotask();
  }
}

interface Progress {
  completed: number;
  inOp: boolean;
  finished: boolean;
}

class StressRun {
  readonly #Target: Constructor;
  readonly #job: ConcurrentJob;
  readonly #testCase: StressCase;
  readonly #sections = new Sections();
  readonly #progress: Progress[];
  readonly #outputs: unknown[][];
  #instance: object = {};
  #failure: StressFailure | null = null;
  #stopped = false;
  #wake: () => void = () => {};

  constructor(Target: Constructor, job: ConcurrentJob, testCase: StressCase) {
    this.#Target = Target;
    this.#job = job;
    this.#testCase = testCase;
    this.#progress = testCase.workers.map(() => ({ completed: 0, inOp: false, finished: false }));
    this.#outputs = testCase.workers.map((worker) => worker.ops.map(() => null));
  }

  async run(): Promise<Fields> {
    const { setup, workers, final } = this.#testCase;
    const plan = {
      setup: this.#steps(setup, "setup", null, 0),
      workers: workers.map((worker, ordinal) => this.#steps(worker, "worker", ordinal, 1)),
      final: final === null ? [] : this.#steps(final, "final", null, 1),
    };
    const setupOutputs = await this.#sequence(plan.setup, "setup", true);
    let openGate: () => void = () => {};
    const gate = new Promise<void>((resolve) => {
      openGate = resolve;
    });
    const settled = new Promise<void>((resolve) => {
      this.#wake = resolve;
    });
    const running = plan.workers.map((steps, ordinal) => this.#work(steps, ordinal, gate));
    let timer: NodeJS.Timeout | undefined;
    const deadline = new Promise<void>((resolve) => {
      timer = setTimeout(resolve, this.#testCase.deadlineMs);
    });
    const started = process.hrtime.bigint();
    openGate();
    await Promise.race([settled, deadline]);
    const durationNs = Number(process.hrtime.bigint() - started);
    clearTimeout(timer);
    this.#stopped = true;
    void Promise.allSettled(running);
    if (this.#failure !== null) {
      return { ...this.#failure.fields, progress: this.#unfinished(), duration_ns: durationNs };
    }
    if (!this.#progress.every((worker) => worker.finished)) {
      return { status: "stalled", progress: this.#unfinished(), duration_ns: durationNs };
    }
    const finalOutputs = await this.#sequence(plan.final, "final", false);
    return {
      status: "ok",
      output: { setup: setupOutputs, workers: this.#outputs, final: finalOutputs },
      sections: this.#sections.snapshot(),
      duration_ns: durationNs,
    };
  }

  /** Step 1: every argument decoded before anything runs. */
  #steps(script: Script, phase: string, worker: number | null, first: number): Step[] {
    return script.ops.map((op, index) => {
      const args = script.args[index] ?? [];
      if (op.startsWith(HARNESS_PREFIX)) {
        return { op, args };
      }
      const prepared = prepare(this.#job, index + first, op, args);
      if ("status" in prepared) {
        throw new StressFailure({ ...prepared, ...location(phase, index, worker) });
      }
      return prepared;
    });
  }

  async #sequence(steps: readonly Step[], phase: string, constructs: boolean): Promise<unknown[]> {
    const outputs: unknown[] = [];
    for (const [index, step] of steps.entries()) {
      try {
        if (constructs && index === 0 && "member" in step) {
          this.#instance = new this.#Target(...step.args);
          outputs.push(null);
        } else {
          outputs.push(await this.#execute(step, []));
        }
      } catch (error) {
        throw new StressFailure({
          ...failureFields(error, `${phase} op ${index}`),
          ...location(phase, index, null),
        });
      }
    }
    return outputs;
  }

  async #execute(step: Step, entered: string[][]): Promise<unknown> {
    if (!("member" in step)) {
      await this.#harness(step, entered);
      return null;
    }
    const value = await callMethod(this.#instance, step, this.#job);
    return serializeResult(step.member, value, step.args, step.watched);
  }

  async #harness(step: Harness, entered: string[][]): Promise<void> {
    const [first, second] = step.args;
    if (step.op === "@enter" && typeof first === "string" && typeof second === "string") {
      this.#sections.enter(first, second);
      entered.push([first, second]);
    } else if (step.op === "@exit" && typeof first === "string") {
      const index = entered.findLastIndex(([name]) => name === first);
      if (index < 0) {
        throw new HarnessError(`@exit "${first}" without a matching @enter`);
      }
      const [[, mode = "exclusive"] = []] = entered.splice(index, 1);
      this.#sections.exit(first, mode);
    } else if (
      step.op === "@pause" &&
      typeof first === "number" &&
      first >= 1 &&
      first <= MAX_PAUSE
    ) {
      await yieldTimes(first);
    } else {
      throw new HarnessError(`${step.op} cannot take ${JSON.stringify(step.args)}`);
    }
  }

  async #work(steps: readonly Step[], ordinal: number, gate: Promise<void>): Promise<void> {
    const random = mulberry32(this.#testCase.seed * PRNG_MULTIPLIER + ordinal);
    const { yieldProbability, maxYields } = this.#testCase.perturb;
    const progress = this.#progress[ordinal] as Progress;
    const outputs = this.#outputs[ordinal] as unknown[];
    const entered: string[][] = [];
    await gate;
    for (const [index, step] of steps.entries()) {
      if (this.#stopped) {
        return;
      }
      if (random() < yieldProbability) {
        await yieldTimes(1 + Math.floor(random() * maxYields));
      }
      progress.inOp = true;
      try {
        outputs[index] = await this.#execute(step, entered);
      } catch (error) {
        this.#fail(
          new StressFailure({
            ...failureFields(error, `worker ${ordinal} op ${index}`),
            ...location("worker", index, ordinal),
          }),
        );
        return;
      }
      progress.completed = index + 1;
      progress.inOp = false;
    }
    progress.finished = true;
    if (this.#progress.every((worker) => worker.finished)) {
      this.#wake();
    }
  }

  #fail(failure: StressFailure): void {
    this.#failure ??= failure;
    this.#wake();
  }

  #unfinished(): Fields[] {
    return this.#progress.flatMap((worker, ordinal) =>
      worker.finished ? [] : [{ worker: ordinal, completed: worker.completed, in_op: worker.inOp }],
    );
  }
}

function location(phase: string, index: number, worker: number | null): Fields {
  return worker === null
    ? { phase, op_index: index }
    : { phase, op_index: index, worker };
}

async function runStress(
  Target: Constructor,
  job: ConcurrentJob,
  testCase: StressCase,
): Promise<Fields> {
  const capture = new OutputCapture();
  capture.start();
  let fields: Fields;
  try {
    fields = await new StressRun(Target, job, testCase).run();
  } catch (error) {
    fields =
      error instanceof StressFailure
        ? { ...error.fields, duration_ns: 0 }
        : { ...failureFields(error, "stress run"), phase: "setup", op_index: 0, duration_ns: 0 };
  }
  const stdout = capture.stop();
  return stdout === "" ? fields : { ...fields, stdout };
}
