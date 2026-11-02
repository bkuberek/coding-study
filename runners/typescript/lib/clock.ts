// Grading jobs on the virtual clock (docs/specs/runners.md#virtual-clock-and-stress-in-project-
// jobs).
//
// Each case runs on a clock of its own (virtual-clock.ts), from the constructor on. The runner
// makes each operation's call, waits for a thenable result while the clock moves to each due
// timer, then settles, so the next operation sees every promise continuation run. The harness
// operations move the clock (`@advance`), start a call without waiting for it (`@spawn`), wait
// for that call (`@join`) and read the clock (`@now`).
//
// A wait that no timer can end ends the case at once as `stalled`, naming the operation and the
// virtual time. Promises still pending when a case ends are dropped, and the mocks are reset, so
// no timer reaches the next case. `duration_ns` is the real time of the whole case.

import { mock } from "node:test";
import { OutputCapture } from "./capture.ts";
import { InvalidInput, InvalidOutput } from "./codec.ts";
import {
  type Constructor,
  decodeArguments,
  invalidInput,
  loadTarget,
  memberOf,
  serializeResult,
  type WatchedInputs,
  watchInputs,
} from "./execute.ts";
import { describeThrown } from "./failures.ts";
import type {
  ClassJob,
  ErrorInfo,
  EventWriter,
  MemberSpec,
  OperationCase,
} from "./protocol.ts";
import {
  DeadlockError,
  type RunningClock,
  startClock,
} from "./virtual-clock.ts";

const HARNESS_PREFIX = "@";
const ADVANCE = "@advance";
const SPAWN = "@spawn";
const JOIN = "@join";
const NOW = "@now";

type Fields = Record<string, unknown>;

export async function runClockJob(
  job: ClassJob,
  events: EventWriter,
): Promise<void> {
  events.write({ event: "job_start", job_id: job.jobId });
  const loaded = await loadTarget(job);
  if (!("shape" in loaded)) {
    events.write({ event: "load_error", job_id: job.jobId, error: loaded });
  } else if (loaded.shape === "class") {
    for (const testCase of job.cases) {
      const ids = { job_id: job.jobId, case_id: testCase.id };
      events.write({ event: "case_start", ...ids });
      const result = await clockCase(loaded.target, job, testCase);
      events.write({ event: "case_result", ...ids, ...result });
    }
  }
  events.write({ event: "job_end", job_id: job.jobId });
}

/** One case on a clock of its own, from the constructor on. */
export async function clockCase(
  Target: Constructor,
  job: ClassJob,
  testCase: OperationCase,
): Promise<Fields> {
  const capture = new OutputCapture();
  capture.start();
  const started = process.hrtime.bigint();
  const clock = startClock(mock.timers);
  let fields: Fields;
  try {
    fields = await new ClockCase(Target, job, clock).run(testCase);
  } finally {
    clock.stop();
  }
  const durationNs = Number(process.hrtime.bigint() - started);
  const stdout = capture.stop();
  const measured = { ...fields, duration_ns: durationNs };
  return stdout === "" ? measured : { ...measured, stdout };
}

/** Ends a case early with its outcome: the error of an operation, or its invalid output. */
class CaseEnded extends Error {
  readonly fields: Fields;

  constructor(fields: Fields) {
    super(String(fields.status));
    this.fields = fields;
  }
}

/** A call that `@spawn` started; `@join` waits for it. */
interface Task {
  readonly member: MemberSpec;
  readonly args: unknown[];
  readonly watched: WatchedInputs;
  readonly result: Promise<Outcome>;
}

type Outcome =
  | { readonly ok: true; readonly value: unknown }
  | { readonly ok: false; readonly error: unknown };

/** One case on the virtual clock: the constructor, then each operation on the new instance. */
class ClockCase {
  readonly #Target: Constructor;
  readonly #job: ClassJob;
  readonly #clock: RunningClock;
  readonly #outputs: unknown[] = [];
  readonly #tasks = new Map<string, Task>();
  #instance: object = {};
  #index = 0;
  #label = "";

  constructor(Target: Constructor, job: ClassJob, clock: RunningClock) {
    this.#Target = Target;
    this.#job = job;
    this.#clock = clock;
  }

  async run(testCase: OperationCase): Promise<Fields> {
    try {
      for (const [index, op] of testCase.ops.entries()) {
        const args = testCase.args[index] ?? [];
        this.#enter(index, op, args);
        this.#outputs.push(await this.#operation(index, op, args));
        await this.#clock.settle();
      }
    } catch (error) {
      if (error instanceof CaseEnded) {
        return error.fields;
      }
      if (error instanceof DeadlockError) {
        return this.#deadlocked(error);
      }
      throw error;
    }
    return { status: "ok", output: this.#outputs };
  }

  /** Records the operation in progress, which a deadlock names: a task's name follows `@spawn`
   * and `@join`. */
  #enter(index: number, op: string, args: readonly unknown[]): void {
    this.#index = index;
    const named = (op === SPAWN || op === JOIN) && typeof args[0] === "string";
    this.#label = named ? `${op} ${String(args[0])}` : op;
  }

  async #operation(
    index: number,
    op: string,
    json: readonly unknown[],
  ): Promise<unknown> {
    if (index !== 0 && op.startsWith(HARNESS_PREFIX)) {
      return this.#harness(op, json);
    }
    const member = this.#input(() => memberOf(this.#job, index, op));
    const args = this.#input(() => decodeArguments(member.params, json));
    const watched = watchInputs(member, args);
    if (index === 0) {
      this.#instance = this.#invoke(() => new this.#Target(...args)) as object;
      return null;
    }
    const value = this.#invoke(() => this.#method(op, args));
    const result = await this.#settled(value);
    return this.#encoded(member, result, args, watched);
  }

  async #harness(op: string, json: readonly unknown[]): Promise<unknown> {
    switch (op) {
      case ADVANCE:
        await this.#clock.advance(this.#input(() => milliseconds(json)));
        return null;
      case SPAWN:
        this.#spawn(json);
        return null;
      case JOIN:
        return this.#join(json);
      case NOW:
        if (json.length > 0) {
          throw this.#inputError(`${NOW} takes no arguments`);
        }
        return this.#clock.now();
      default:
        throw this.#inputError(
          `unknown harness operation "${op}" at index ${this.#index}`,
        );
    }
  }

  #spawn(json: readonly unknown[]): void {
    const [task, method, ...rest] = json;
    if (typeof task !== "string" || typeof method !== "string") {
      throw this.#inputError(
        `${SPAWN} takes a task name, a method and its arguments`,
      );
    }
    if (this.#tasks.has(task)) {
      throw this.#inputError(`task "${task}" was spawned and not joined yet`);
    }
    const spec = this.#job.methods.get(method);
    if (spec === undefined) {
      throw this.#inputError(`${SPAWN} of an unknown method "${method}"`);
    }
    const member = spec.member;
    const args = this.#input(() => decodeArguments(member.params, rest));
    const watched = watchInputs(member, args);
    const value = this.#invoke(() => this.#method(method, args));
    this.#tasks.set(task, { member, args, watched, result: outcome(value) });
  }

  async #join(json: readonly unknown[]): Promise<unknown> {
    const [task] = json;
    if (typeof task !== "string" || json.length !== 1) {
      throw this.#inputError(`${JOIN} takes the name of a spawned task`);
    }
    const spawned = this.#tasks.get(task);
    if (spawned === undefined) {
      throw this.#inputError(
        `${JOIN} of task "${task}", which no ${SPAWN} started`,
      );
    }
    this.#tasks.delete(task);
    const result = await this.#clock.wait(spawned.result);
    if (!result.ok) {
      throw this.#ended(describeThrown(result.error));
    }
    const { member, args, watched } = spawned;
    return this.#encoded(member, result.value, args, watched);
  }

  #method(op: string, args: unknown[]): unknown {
    const spec = this.#job.methods.get(op);
    const callable = (this.#instance as Record<string, unknown>)[
      spec?.memberName ?? op
    ];
    if (typeof callable !== "function") {
      throw new TypeError(`${this.#job.exportName} has no method "${op}"`);
    }
    return Reflect.apply(callable, this.#instance, args);
  }

  /** The value of a thenable, the clock moving while it is pending, else the value. */
  async #settled(value: unknown): Promise<unknown> {
    if (!isThenable(value)) {
      return value;
    }
    const result = await this.#clock.wait(outcome(value));
    if (!result.ok) {
      throw this.#ended(describeThrown(result.error));
    }
    return result.value;
  }

  /** Calls user code; what it throws ends the case as the operation's error. */
  #invoke(call: () => unknown): unknown {
    try {
      return call();
    } catch (error) {
      throw this.#ended(describeThrown(error));
    }
  }

  /** Decodes what the case gives; a failure ends the case as the operation's input error. */
  #input<T>(decode: () => T): T {
    try {
      return decode();
    } catch (error) {
      if (error instanceof InvalidInput) {
        throw this.#ended(invalidInput(error));
      }
      throw error;
    }
  }

  #encoded(
    member: MemberSpec,
    result: unknown,
    args: unknown[],
    watched: WatchedInputs,
  ): unknown {
    try {
      return serializeResult(member, result, args, watched);
    } catch (error) {
      if (error instanceof InvalidOutput) {
        throw new CaseEnded({
          status: "invalid_output",
          reason: `op ${this.#index} (${this.#label}): ${error.message}`,
        });
      }
      throw error;
    }
  }

  #inputError(message: string): CaseEnded {
    return this.#ended(invalidInput(new InvalidInput(message)));
  }

  #ended(error: ErrorInfo): CaseEnded {
    return new CaseEnded({
      status: "error",
      error,
      op_index: this.#index,
      partial_output: [...this.#outputs],
    });
  }

  #deadlocked(deadlock: DeadlockError): Fields {
    const at = deadlock.milliseconds;
    return {
      status: "stalled",
      op_index: this.#index,
      reason: `op ${this.#index} (${this.#label}): deadlock at ${at} ms`,
      partial_output: [...this.#outputs],
    };
  }
}

function milliseconds(json: readonly unknown[]): number {
  const [value] = json;
  if (json.length !== 1 || !Number.isInteger(value) || (value as number) < 0) {
    throw new InvalidInput(
      `${ADVANCE} takes a whole number of milliseconds, 0 or more`,
    );
  }
  return value as number;
}

/** Follows a call's result from the moment it starts, so a rejection is handled even before
 * `@join` waits for it; never rejects. */
function outcome(value: unknown): Promise<Outcome> {
  return Promise.resolve(value).then(
    (resolved): Outcome => ({ ok: true, value: resolved }),
    (error: unknown): Outcome => ({ ok: false, error }),
  );
}

function isThenable(value: unknown): value is PromiseLike<unknown> {
  return (
    (typeof value === "object" || typeof value === "function") &&
    value !== null &&
    typeof (value as { then?: unknown }).then === "function"
  );
}
