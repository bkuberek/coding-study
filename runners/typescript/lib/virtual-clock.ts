// The virtual clock of a TypeScript project (docs/specs/runners.md#virtual-clock-and-stress-in-
// project-jobs). `cstudy submit` grades each case on it, and the generated tests in `tests/` run
// on it through a copy of this file, so your tests and the grader share one clock.
//
// It drives `node:test`'s mock timers (`setTimeout`, `setInterval` and `Date`), which move only
// when told to. The clock starts at 0 and moves to each timer's due time in turn, letting promise
// continuations run (one real macrotask) before the next, so every callback and every `await`
// after a sleep sees its own time: a wait of any length takes no real time. Timers due at the same
// instant fire in the order they were set.
//
// Code reads the time with `Date.now()` and waits with `setTimeout`, `setInterval` or
// `setTimeout` from `node:timers/promises`, looked up when it waits: a timer function stored
// before the clock started is the real one, which the clock cannot move. A wait that no timer of
// the clock can end is a deadlock: `wait` throws a `DeadlockError` at once.

import { createRequire, syncBuiltinESMExports } from "node:module";
import type { MockTimers, TestContext } from "node:test";

const require = createRequire(import.meta.url);

type TimerFunction = (
  callback: (...args: unknown[]) => void,
  ms?: number,
  ...args: unknown[]
) => unknown;
type ClearFunction = (handle: unknown) => void;
type SleepFunction = (
  ms?: number,
  value?: unknown,
  options?: unknown,
) => Promise<unknown>;

interface TimersModule {
  setTimeout: TimerFunction;
  setInterval: TimerFunction;
  clearTimeout: ClearFunction;
  clearInterval: ClearFunction;
}

interface TimersPromisesModule {
  setTimeout: SleepFunction;
}

/** A timer of the clock: the mock's handle, which knows when it is due, or a sleep's entry. */
interface Due {
  readonly runAt?: unknown;
}

const timers = require("node:timers") as TimersModule;
const timersPromises = require("node:timers/promises") as TimersPromisesModule;
const globals = globalThis as unknown as TimersModule;
const realSetImmediate = setImmediate;
const MOCKED_APIS = ["setTimeout", "setInterval", "Date"] as const;

/** Every task waits and no timer of the clock is due: nothing can wake a task. */
export class DeadlockError extends Error {
  readonly milliseconds: number;

  constructor(milliseconds: number) {
    super(
      `deadlock: every task waits and no timer is due, at ${milliseconds} ms`,
    );
    this.name = "DeadlockError";
    this.milliseconds = milliseconds;
  }
}

export interface VirtualClock {
  /** The virtual milliseconds since the clock started. */
  now(): number;
  /** Lets every promise continuation run, without moving the clock. */
  settle(): Promise<void>;
  /** Moves the clock forward; each timer due on the way fires at its own time, and the code
   * settles after each. */
  advance(milliseconds: number): Promise<void>;
  /** The value of a promise, the clock moving to each due timer while it is pending; throws a
   * `DeadlockError` when no timer is due while it is still pending. */
  wait<T>(value: T | PromiseLike<T>): Promise<T>;
}

/** A clock that `stop` ends: the mocks are reset and the real timers return. */
export interface RunningClock extends VirtualClock {
  stop(): void;
}

/** The clock of one test: it starts now and stops when the test ends. */
export function virtualClock(context: TestContext): VirtualClock {
  const clock = startClock(context.mock.timers);
  context.after(() => clock.stop());
  return clock;
}

/** The clock on `mockTimers`, which must not be enabled yet. */
export function startClock(mockTimers: MockTimers): RunningClock {
  mockTimers.enable({ apis: MOCKED_APIS, now: 0 });
  const state = new ClockState(mockTimers);
  state.install();
  syncBuiltinESMExports();
  return state;
}

class ClockState implements RunningClock {
  readonly #mockTimers: MockTimers;
  readonly #due = new Set<Due>();
  #stopped = false;

  constructor(mockTimers: MockTimers) {
    this.#mockTimers = mockTimers;
  }

  /** Puts the clock's bookkeeping around each mocked timer function. */
  install(): void {
    const mocked = {
      setTimeout: globals.setTimeout,
      setInterval: globals.setInterval,
      clearTimeout: globals.clearTimeout,
      clearInterval: globals.clearInterval,
    };
    const sleep = timersPromises.setTimeout;
    const tracked: TimersModule = {
      setTimeout: (callback, ms, ...args) => {
        const handle = mocked.setTimeout(
          (...called: unknown[]) => {
            this.#due.delete(handle as Due);
            callback(...called);
          },
          ms,
          ...args,
        );
        this.#due.add(handle as Due);
        return handle;
      },
      setInterval: (callback, ms, ...args) => {
        const handle = mocked.setInterval(callback, ms, ...args);
        this.#due.add(handle as Due);
        return handle;
      },
      clearTimeout: (handle) => {
        this.#due.delete(handle as Due);
        mocked.clearTimeout(handle);
      },
      clearInterval: (handle) => {
        this.#due.delete(handle as Due);
        mocked.clearInterval(handle);
      },
    };
    Object.assign(globals, tracked);
    Object.assign(timers, tracked);
    timersPromises.setTimeout = (ms, value, options) => {
      const delay = Number.isFinite(ms) ? Number(ms) : 0;
      const entry: Due = { runAt: Date.now() + delay };
      this.#due.add(entry);
      return sleep(ms, value, options).finally(() => this.#due.delete(entry));
    };
  }

  stop(): void {
    if (this.#stopped) {
      return;
    }
    this.#stopped = true;
    this.#due.clear();
    this.#mockTimers.reset();
    syncBuiltinESMExports();
  }

  now(): number {
    return Date.now();
  }

  async settle(): Promise<void> {
    await new Promise<void>((resolve) => realSetImmediate(resolve));
  }

  async advance(milliseconds: number): Promise<void> {
    const target = Date.now() + milliseconds;
    await this.settle();
    let next = this.#nextDue();
    while (next !== undefined && next <= target) {
      this.#tickTo(next);
      await this.settle();
      next = this.#nextDue();
    }
    this.#tickTo(target);
    await this.settle();
  }

  async wait<T>(value: T | PromiseLike<T>): Promise<T> {
    const outcome = settled(value);
    for (;;) {
      await this.settle();
      const result = outcome.result;
      if (result !== undefined) {
        if (result.ok) {
          return result.value;
        }
        throw result.error;
      }
      const next = this.#nextDue();
      if (next === undefined) {
        throw new DeadlockError(Date.now());
      }
      this.#tickTo(next);
    }
  }

  /** The time of the earliest timer of the clock; one whose time is not a number is due now. */
  #nextDue(): number | undefined {
    let next: number | undefined;
    for (const due of this.#due) {
      const runAt =
        typeof due.runAt === "number" && !Number.isNaN(due.runAt)
          ? due.runAt
          : Date.now();
      next = next === undefined ? runAt : Math.min(next, runAt);
    }
    return next;
  }

  #tickTo(time: number): void {
    this.#mockTimers.tick(Math.max(0, time - Date.now()));
  }
}

type Result<T> =
  | { readonly ok: true; readonly value: T }
  | { readonly ok: false; readonly error: unknown };

/** Follows a value's settlement from now on, so a rejection is handled even before anyone
 * waits. */
function settled<T>(value: T | PromiseLike<T>): {
  readonly result: Result<T> | undefined;
} {
  const outcome: { result: Result<T> | undefined } = { result: undefined };
  Promise.resolve(value).then(
    (resolved) => {
      outcome.result = { ok: true, value: resolved };
    },
    (error: unknown) => {
      outcome.result = { ok: false, error };
    },
  );
  return outcome;
}
