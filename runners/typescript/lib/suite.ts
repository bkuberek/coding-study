// A suite job: a project's own tests, run by `node:test` inside the runner
// (docs/specs/runners.md#suite-job).
//
// `run({ files, isolation: "none", concurrency: 1 })` imports every test file into this process and
// runs one test at a time. Its stream emits `test:dequeue` synchronously just before a test runs and
// `test:complete` just after it ends, so `case_start` is written before user code runs, and the
// CLI's hang guard and crash handling see the test in progress; what the test prints in between is
// captured. Subtests (`t.test`) belong to their test: they are not reported apart, and the first one
// that fails explains its test's failure.
//
// With isolation "none", Node takes test name patterns from its own command line only, so the
// runner leaves tests out itself: a `beforeEach` hook registered before any file loads throws
// before the body of a test that `select` does not name or `skip` lists, and nothing is reported
// for that test.

import { AssertionError } from "node:assert";
import { existsSync, globSync, realpathSync } from "node:fs";
import { join, relative } from "node:path";
import { finished } from "node:stream/promises";
import { beforeEach, run, type EventData } from "node:test";
import { OutputCapture } from "./capture.ts";
import { describeThrown } from "./failures.ts";
import type { ErrorInfo, EventWriter, SuiteJob } from "./protocol.ts";

/** The files `node --test` runs when given none (Node 24, which strips types by default). */
const TEST_FILE_PATTERN =
  "**/{test,test/**/*,test-*,*[._-]test}.{js,mjs,cjs,ts,mts,cts}";
const DEPENDENCIES_DIRECTORY = "node_modules";
const ID_SEPARATOR = "::";
const NAME_SEPARATOR = " > ";
const SUITE = "suite";
const SUBTESTS_FAILED = "subtestsFailed";
const CANCELLED_BY_PARENT = "cancelledByParent";
const TODO = "todo";

type Completion = EventData.TestComplete;

/** What a suite job reports for one test, without its ids, duration and output. */
type TestResult =
  | { readonly status: "ok" }
  | {
      readonly status: "failed";
      readonly message: string;
      readonly expected?: unknown;
      readonly actual?: unknown;
    }
  | { readonly status: "error"; readonly error: ErrorInfo }
  | { readonly status: "skipped"; readonly message: string };

export async function runSuiteJob(
  job: SuiteJob,
  events: EventWriter,
): Promise<void> {
  events.write({ event: "job_start", job_id: job.jobId });
  if (existsSync(job.root)) {
    await new SuiteRun(job, events).run();
  } else {
    const error = {
      type: "FileNotFound",
      message: `no such folder: ${job.root}`,
    };
    events.write({ event: "load_error", job_id: job.jobId, error });
  }
  events.write({ event: "job_end", job_id: job.jobId });
}

/** The test ids a suite job runs: `select` (whole ids or their last part) without `skip`. */
class Selection {
  readonly #select: readonly string[];
  readonly #skip: ReadonlySet<string>;

  constructor(job: SuiteJob) {
    this.#select = job.select;
    this.#skip = new Set(job.skip);
  }

  skips(id: string): boolean {
    return this.#skip.has(id);
  }

  runs(id: string): boolean {
    if (this.#skip.has(id)) {
      return false;
    }
    return (
      this.#select.length === 0 ||
      this.#select.some(
        (wanted) => id === wanted || id.endsWith(`${ID_SEPARATOR}${wanted}`),
      )
    );
  }

  /**
   * A file that does not import is reported unless `select` names only tests of other files; a
   * last part alone names a test at the top of any file.
   */
  reportsFile(file: string): boolean {
    return this.#reports(
      file,
      (wanted) =>
        !wanted.includes(ID_SEPARATOR) ||
        wanted.startsWith(`${file}${ID_SEPARATOR}`),
    );
  }

  /**
   * A block that failed on its own is reported unless `select` names only tests outside it; a
   * last part alone never names a test in a block.
   */
  reportsBlock(id: string): boolean {
    return this.#reports(id, (wanted) =>
      wanted.startsWith(`${id}${NAME_SEPARATOR}`),
    );
  }

  #reports(id: string, within: (wanted: string) => boolean): boolean {
    if (this.#skip.has(id)) {
      return false;
    }
    return (
      this.#select.length === 0 ||
      this.#select.some((wanted) => wanted === id || within(wanted))
    );
  }
}

/** The test that is running, from its `test:dequeue` to its `test:complete`. */
interface CurrentTest {
  readonly testId: number;
  readonly nesting: number;
  readonly id: string;
  readonly runs: boolean;
  readonly started: bigint;
  readonly capture: OutputCapture;
  /** The first of its subtests that failed. */
  failedSubtest: Completion | null;
}

class SuiteRun {
  readonly #job: SuiteJob;
  readonly #events: EventWriter;
  readonly #selection: Selection;
  readonly #root: string;
  /** Each file as `run` names it (absolute), to its path relative to the root. */
  readonly #files = new Map<string, string>();
  /** Whether each test is a block (`describe`) or a test; `test:dequeue` can misreport it. */
  readonly #kinds = new Map<number, "suite" | "test">();
  /** The blocks enclosing the next test, outermost first. */
  readonly #blocks: string[] = [];
  #current: CurrentTest | null = null;

  constructor(job: SuiteJob, events: EventWriter) {
    this.#job = job;
    this.#events = events;
    this.#selection = new Selection(job);
    this.#root = realpathSync(job.root);
  }

  async run(): Promise<void> {
    for (const file of this.#testFiles()) {
      this.#files.set(join(this.#root, file), file);
    }
    if (this.#files.size === 0) {
      return;
    }
    const stream = run({
      files: [...this.#files.keys()],
      isolation: "none",
      concurrency: 1,
      cwd: this.#root,
      setup: () => beforeEach(() => this.#leaveOut()),
    });
    stream.on("test:enqueue", (data) =>
      this.#kinds.set(data.testId, data.type),
    );
    stream.on("test:dequeue", (data) => this.#dequeued(data));
    stream.on("test:complete", (data) => this.#completed(data));
    await finished(stream.resume());
  }

  /** As `node --test` finds them, in path order, without excluded files and failed imports. */
  #testFiles(): string[] {
    const excluded = new Set(this.#job.exclude);
    return globSync(TEST_FILE_PATTERN, {
      cwd: this.#root,
      exclude: (name) => name === DEPENDENCIES_DIRECTORY,
    })
      .filter((file) => !excluded.has(file) && !this.#selection.skips(file))
      .sort();
  }

  /** Runs in `beforeEach`: a test that is not to run throws before its body. */
  #leaveOut(): void {
    if (this.#current?.runs === false) {
      throw new Error("left out of this run");
    }
  }

  #dequeued(data: EventData.TestDequeue): void {
    if (this.#current !== null) {
      return;
    }
    if ((this.#kinds.get(data.testId) ?? data.type) === SUITE) {
      this.#blocks.length = data.nesting;
      this.#blocks.push(data.name);
      return;
    }
    const id = this.#id(data);
    const runs = this.#reports(data, id);
    this.#current = {
      testId: data.testId,
      nesting: data.nesting,
      id,
      runs,
      started: process.hrtime.bigint(),
      capture: new OutputCapture(),
      failedSubtest: null,
    };
    if (runs) {
      this.#events.write({
        event: "case_start",
        job_id: this.#job.jobId,
        case_id: id,
      });
      this.#current.capture.start();
    }
  }

  #completed(data: Completion): void {
    const current = this.#current;
    if (current?.testId === data.testId) {
      this.#current = null;
      if (current.runs) {
        const stdout = current.capture.stop();
        const durationNs = process.hrtime.bigint() - current.started;
        this.#result(
          current.id,
          testResult(data, current.failedSubtest),
          durationNs,
          stdout,
        );
      }
    } else if (current !== null) {
      if (data.nesting > current.nesting && !data.details.passed) {
        current.failedSubtest ??= data;
      }
    } else if ((this.#kinds.get(data.testId) ?? data.details.type) === SUITE) {
      this.#blockCompleted(data);
    } else {
      this.#notStarted(data);
    }
  }

  /** A block that failed on its own (its body threw, or a hook failed) is one `error`. */
  #blockCompleted(data: Completion): void {
    const id = this.#id(data);
    this.#blocks.length = data.nesting;
    const reason = failureType(data.details.error);
    const failedItself =
      reason !== SUBTESTS_FAILED && reason !== CANCELLED_BY_PARENT;
    if (
      !data.details.passed &&
      failedItself &&
      this.#selection.reportsBlock(id)
    ) {
      this.#startAndEnd(id, testResult(data, null));
    }
  }

  /** A test that ended without starting, cancelled by a hook of its block. */
  #notStarted(data: Completion): void {
    const id = this.#id(data);
    if (this.#reports(data, id)) {
      this.#startAndEnd(id, testResult(data, null));
    }
  }

  /** `node:test` reports a file that does not import as a failed test named after the file. */
  #reports(data: EventData.TestDequeue | Completion, id: string): boolean {
    return this.#isFile(data)
      ? this.#selection.reportsFile(id)
      : this.#selection.runs(id);
  }

  #isFile(data: { readonly name: string; readonly nesting: number }): boolean {
    return data.nesting === 0 && this.#files.has(data.name);
  }

  #startAndEnd(id: string, result: TestResult): void {
    this.#events.write({
      event: "case_start",
      job_id: this.#job.jobId,
      case_id: id,
    });
    this.#result(id, result, 0n, "");
  }

  #result(
    id: string,
    result: TestResult,
    durationNs: bigint,
    stdout: string,
  ): void {
    this.#events.write({
      event: "case_result",
      job_id: this.#job.jobId,
      case_id: id,
      ...result,
      duration_ns: Number(durationNs),
      ...(stdout === "" ? {} : { stdout }),
    });
  }

  /**
   * `<file relative to the root>::<names from the outermost block, joined by " > ">`; a file that
   * does not import is reported under its path, which `node:test` uses as the test's name.
   */
  #id(data: {
    readonly name: string;
    readonly nesting: number;
    readonly file?: string;
  }): string {
    const file = this.#files.get(data.name);
    if (file !== undefined && this.#isFile(data)) {
      return file;
    }
    const path = data.file === undefined ? "" : relative(this.#root, data.file);
    const names = [...this.#blocks.slice(0, data.nesting), data.name];
    return `${path}${ID_SEPARATOR}${names.join(NAME_SEPARATOR)}`;
  }
}

function testResult(
  data: Completion,
  failedSubtest: Completion | null,
): TestResult {
  if (data.skip !== undefined) {
    return { status: "skipped", message: reason(data.skip) };
  }
  if (data.details.passed) {
    return { status: "ok" };
  }
  if (data.todo !== undefined) {
    const why = reason(data.todo);
    return {
      status: "skipped",
      message: why === "" ? TODO : `${TODO}: ${why}`,
    };
  }
  const error = data.details.error;
  if (failureType(error) === SUBTESTS_FAILED && failedSubtest !== null) {
    return named(failedSubtest.name, testResult(failedSubtest, null));
  }
  return thrownResult(error?.cause ?? error);
}

/** An assertion of `node:assert` is `failed`, with both sides when both are JSON values. */
function thrownResult(thrown: unknown): TestResult {
  if (!(thrown instanceof AssertionError)) {
    return { status: "error", error: describeThrown(thrown) };
  }
  const { expected, actual } = thrown;
  const sides = isJson(expected) && isJson(actual) ? { expected, actual } : {};
  return { status: "failed", message: thrown.message, ...sides };
}

/** The result of a test that failed in its subtest `name`, which the message names. */
function named(name: string, result: TestResult): TestResult {
  switch (result.status) {
    case "failed":
      return { ...result, message: `${name}: ${result.message}` };
    case "error":
      return {
        ...result,
        error: { ...result.error, message: `${name}: ${result.error.message}` },
      };
    default:
      return result;
  }
}

/** Why `node:test` failed a test (`testCodeFailure`, `hookFailed`, `subtestsFailed`, ...). */
function failureType(error: unknown): unknown {
  return typeof error === "object" && error !== null
    ? (error as { failureType?: unknown }).failureType
    : undefined;
}

function reason(directive: string | boolean): string {
  return typeof directive === "string" ? directive : "";
}

/** Whether `value` is a JSON value as it is: no `undefined`, functions, class instances or cycles. */
function isJson(value: unknown, enclosing: Set<unknown> = new Set()): boolean {
  if (
    value === null ||
    typeof value === "string" ||
    typeof value === "boolean"
  ) {
    return true;
  }
  if (typeof value === "number") {
    return Number.isFinite(value);
  }
  if (
    typeof value !== "object" ||
    enclosing.has(value) ||
    !isPlainContainer(value)
  ) {
    return false;
  }
  enclosing.add(value);
  const json = Object.values(value).every((item) => isJson(item, enclosing));
  enclosing.delete(value);
  return json;
}

function isPlainContainer(value: object): boolean {
  const prototype = Object.getPrototypeOf(value);
  return (
    Array.isArray(value) || prototype === Object.prototype || prototype === null
  );
}
