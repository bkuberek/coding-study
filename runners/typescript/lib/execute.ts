// Loads a job's target and runs its cases (docs/specs/runners.md#locating-user-code).

import { existsSync } from "node:fs";
import { basename } from "node:path";
import { pathToFileURL } from "node:url";
import { OutputCapture } from "./capture.ts";
import {
  decode,
  describe,
  encode,
  encodeNodeValue,
  InvalidInput,
  InvalidOutput,
  traverse,
} from "./codec.ts";
import { describeThrown } from "./failures.ts";
import type {
  BenchCase,
  CaseStatus,
  ClassJob,
  ErrorInfo,
  EventWriter,
  FunctionCase,
  FunctionJob,
  Job,
  MemberSpec,
  MethodSpec,
  OperationCase,
  ParamSpec,
} from "./protocol.ts";

export type Callable = (...args: unknown[]) => unknown;
export type Constructor = new (...args: unknown[]) => object;
type Exports = Readonly<Record<string, unknown>>;

const INVALID_INPUT = "InvalidInput";

/** A job's target once its file loaded and its export fits the signature. */
export type LoadedTarget =
  | {
      readonly shape: "function";
      readonly job: FunctionJob;
      readonly target: Callable;
    }
  | {
      readonly shape: "class";
      readonly job: ClassJob;
      readonly target: Constructor;
    };

/** What one call through the test path did, and how long user code ran. */
export interface MeasuredRun {
  readonly status: CaseStatus;
  readonly durationNs: number;
  readonly stdout: string;
}

export async function runJob(job: Job, events: EventWriter): Promise<void> {
  events.write({ event: "job_start", job_id: job.jobId });
  const loaded = await loadTarget(job);
  if ("shape" in loaded) {
    const cases: readonly BenchCase[] = loaded.job.cases;
    for (const testCase of cases) {
      runCase(job, testCase.id, events, (stopwatch) =>
        runTestCase(loaded, testCase, stopwatch),
      );
    }
  } else {
    events.write({ event: "load_error", job_id: job.jobId, error: loaded });
  }
  events.write({ event: "job_end", job_id: job.jobId });
}

/** The job's target, or why it does not load. */
export async function loadTarget(job: Job): Promise<LoadedTarget | ErrorInfo> {
  try {
    const exports = await loadExports(job.path);
    if (job.shape === "function") {
      return { shape: "function", job, target: functionExport(exports, job) };
    }
    return { shape: "class", job, target: classExport(exports, job) };
  } catch (error) {
    return error instanceof LoadFailure ? error.info : describeThrown(error);
  }
}

/** One case as `cstudy test` runs it: decoded, called (timed), serialized, output captured. */
export function measuredRun(
  run: (stopwatch: Stopwatch) => CaseStatus,
): MeasuredRun {
  const stopwatch = new Stopwatch();
  const capture = new OutputCapture();
  capture.start();
  let status: CaseStatus;
  let stdout: string;
  try {
    status = run(stopwatch);
  } catch (error) {
    status = unexpectedFailure(error);
  } finally {
    stdout = capture.stop();
  }
  return { status, durationNs: stopwatch.nanoseconds, stdout };
}

export function runTestCase(
  loaded: LoadedTarget,
  testCase: BenchCase,
  stopwatch: Stopwatch,
): CaseStatus {
  if (loaded.shape === "function") {
    return functionCase(loaded.target, loaded.job, asFunctionCase(testCase), stopwatch);
  }
  return new OperationRun(loaded.target, loaded.job, stopwatch).run(
    asOperationCase(testCase),
  );
}

/**
 * Decodes fresh inputs now; the returned call runs user code without timing or serializing
 * (bench mode). A class kind's call runs the whole operation sequence on a new instance.
 */
export function prepareCall(
  loaded: LoadedTarget,
  testCase: BenchCase,
): () => unknown {
  if (loaded.shape === "function") {
    const { member } = loaded.job;
    const input = asFunctionCase(testCase).input;
    const args = decodeArguments(
      member.params,
      member.params.map((param) => input[param.name]),
    );
    const target = loaded.target;
    return () => target(...args);
  }
  const sequence = asOperationCase(testCase);
  const job = loaded.job;
  const members = sequence.ops.map((op, index) => memberOf(job, index, op));
  const args = members.map((member, index) =>
    decodeArguments(member.params, sequence.args[index] ?? []),
  );
  const methods = sequence.ops.map((op) => job.methods.get(op)?.memberName ?? "");
  const Target = loaded.target;
  return () => {
    const instance = new Target(...(args[0] ?? []));
    const results: unknown[] = [instance];
    for (let index = 1; index < args.length; index++) {
      const method = (instance as Record<string, unknown>)[methods[index] ?? ""];
      results.push(Reflect.apply(method as Callable, instance, args[index] ?? []));
    }
    return results;
  };
}

function asFunctionCase(testCase: BenchCase): FunctionCase {
  if (!("input" in testCase)) {
    throw new InvalidInput("a function job takes arguments, not operations");
  }
  return testCase;
}

function asOperationCase(testCase: BenchCase): OperationCase {
  if (!("ops" in testCase)) {
    throw new InvalidInput("a class job takes operations, not arguments");
  }
  return testCase;
}

export function memberOf(job: ClassJob, index: number, op: string): MemberSpec {
  const member = index === 0 ? job.constructorSpec : job.methods.get(op)?.member;
  if (member === undefined) {
    throw new InvalidInput(`unknown operation "${op}"`);
  }
  return member;
}

/** Why a target cannot be loaded; reported as the job's `load_error`. */
class LoadFailure extends Error {
  readonly info: ErrorInfo;

  constructor(type: string, message: string) {
    super(message);
    this.info = { type, message };
  }
}

async function loadExports(path: string): Promise<Exports> {
  if (!existsSync(path)) {
    throw new LoadFailure("FileNotFound", `no such file: ${path}`);
  }
  return (await import(pathToFileURL(path).href)) as Exports;
}

function functionExport(exports: Exports, job: FunctionJob): Callable {
  const target = exports[job.exportName];
  if (typeof target !== "function") {
    throw missingExport(exports, job, "function");
  }
  requireArity(target, job.member.params, job.exportName);
  return target as Callable;
}

function classExport(exports: Exports, job: ClassJob): Constructor {
  const target = exports[job.exportName];
  if (typeof target !== "function") {
    throw missingExport(exports, job, "class");
  }
  // An omitted constructor has no parameters, which is fine when the arguments are unused.
  if (target.length > job.constructorSpec.params.length) {
    requireArity(
      target,
      job.constructorSpec.params,
      `${job.exportName} constructor`,
    );
  }
  const prototype = (target.prototype ?? {}) as Exports;
  for (const { memberName, member } of job.methods.values()) {
    const method = prototype[memberName];
    if (typeof method !== "function") {
      throw new LoadFailure(
        "MissingMethod",
        `${job.exportName} has no method "${memberName}"`,
      );
    }
    requireArity(method, member.params, `${job.exportName}.${memberName}`);
  }
  return target as Constructor;
}

function missingExport(exports: Exports, job: Job, kind: string): LoadFailure {
  const available = Object.keys(exports).join(", ") || "none";
  const file = basename(job.path);
  return new LoadFailure(
    "MissingExport",
    `${file} does not export a ${kind} named "${job.exportName}" (exports: ${available})`,
  );
}

function requireArity(
  target: Function,
  params: readonly ParamSpec[],
  label: string,
): void {
  if (target.length !== params.length) {
    const declared = params.map((param) => param.name).join(", ");
    const message = `${label} takes ${target.length} parameter(s); the signature declares ${params.length} (${declared})`;
    throw new LoadFailure("ArityMismatch", message);
  }
}

function functionCase(
  target: Callable,
  job: FunctionJob,
  testCase: FunctionCase,
  stopwatch: Stopwatch,
): CaseStatus {
  const args = decodeArguments(
    job.member.params,
    job.member.params.map((param) => testCase.input[param.name]),
  );
  const watched = watchInputs(job.member, args);
  let result: unknown;
  try {
    result = stopwatch.time(() => target(...args));
  } catch (thrown) {
    return { status: "error", error: describeThrown(thrown) };
  }
  return {
    status: "ok",
    output: serializeResult(job.member, result, args, watched),
  };
}

/** Runs one operation sequence: `ops[0]` constructs, later ops call methods on the instance. */
class OperationRun {
  readonly #target: Constructor;
  readonly #job: ClassJob;
  readonly #stopwatch: Stopwatch;
  readonly #outputs: unknown[] = [];
  #instance: object = {};

  constructor(target: Constructor, job: ClassJob, stopwatch: Stopwatch) {
    this.#target = target;
    this.#job = job;
    this.#stopwatch = stopwatch;
  }

  run(testCase: OperationCase): CaseStatus {
    for (const [index, op] of testCase.ops.entries()) {
      const failure = this.#step(index, op, testCase.args[index] ?? []);
      if (failure !== null) {
        return failure;
      }
    }
    return { status: "ok", output: this.#outputs };
  }

  #step(
    index: number,
    op: string,
    json: readonly unknown[],
  ): CaseStatus | null {
    try {
      const member = memberOf(this.#job, index, op);
      const args = decodeArguments(member.params, json);
      const watched = watchInputs(member, args);
      let result: unknown;
      try {
        result = this.#stopwatch.time(() => this.#call(index, op, args));
      } catch (thrown) {
        return this.#error(index, describeThrown(thrown));
      }
      this.#outputs.push(
        index === 0 ? null : serializeResult(member, result, args, watched),
      );
      return null;
    } catch (error) {
      if (error instanceof InvalidOutput) {
        return {
          status: "invalid_output",
          reason: `op ${index} (${op}): ${error.message}`,
        };
      }
      return this.#error(
        index,
        error instanceof InvalidInput
          ? invalidInput(error)
          : describeThrown(error),
      );
    }
  }

  #call(index: number, op: string, args: unknown[]): unknown {
    if (index === 0) {
      this.#instance = new this.#target(...args);
      return this.#instance;
    }
    const method = this.#job.methods.get(op) as MethodSpec;
    const callable = (this.#instance as Record<string, unknown>)[
      method.memberName
    ];
    return Reflect.apply(callable as Callable, this.#instance, args);
  }

  #error(index: number, error: ErrorInfo): CaseStatus {
    return {
      status: "error",
      error,
      op_index: index,
      partial_output: [...this.#outputs],
    };
  }
}

function runCase(
  job: Job,
  caseId: string,
  events: EventWriter,
  run: (stopwatch: Stopwatch) => CaseStatus,
): void {
  const ids = { job_id: job.jobId, case_id: caseId };
  events.write({ event: "case_start", ...ids });
  const { status, durationNs, stdout } = measuredRun(run);
  const output = stdout === "" ? {} : { stdout };
  events.write({
    event: "case_result",
    ...ids,
    ...status,
    duration_ns: durationNs,
    ...output,
  });
}

function unexpectedFailure(error: unknown): CaseStatus {
  if (error instanceof InvalidOutput) {
    return { status: "invalid_output", reason: error.message };
  }
  return {
    status: "error",
    error:
      error instanceof InvalidInput
        ? invalidInput(error)
        : describeThrown(error),
  };
}

export function invalidInput(error: InvalidInput): ErrorInfo {
  return { type: INVALID_INPUT, message: error.message };
}

/** Fresh arguments for one call; `ref_of` parameters resolve against their decoded owner. */
export function decodeArguments(
  params: readonly ParamSpec[],
  json: readonly unknown[],
): unknown[] {
  const values = params.map((param, index) =>
    param.refOf === null ? decode(json[index], param.type) : null,
  );
  params.forEach((param, index) => {
    if (param.refOf !== null) {
      values[index] = referencedNode(json[index], param.refOf, params, values);
    }
  });
  return values;
}

function referencedNode(
  val: unknown,
  ownerName: string,
  params: readonly ParamSpec[],
  values: unknown[],
): object | null {
  if (val === null) {
    return null;
  }
  const owner = params.findIndex((param) => param.name === ownerName);
  const nodes =
    owner < 0 ? [] : traverse(values[owner], (params[owner] as ParamSpec).type);
  const node = nodes.find(
    (candidate) => (candidate as { val?: unknown }).val === val,
  );
  if (node === undefined) {
    throw new InvalidInput(`no node with val ${describe(val)} in ${ownerName}`);
  }
  return node;
}

/** What `as: index` and `no_alias_with` compare against, captured before the call. */
export interface WatchedInputs {
  readonly order: readonly object[];
  readonly aliased: ReadonlySet<object>;
}

export function watchInputs(member: MemberSpec, args: unknown[]): WatchedInputs {
  const { of, noAliasWith } = member.returns;
  return {
    order: of === null ? [] : reachable(member, args, of),
    aliased: new Set(
      noAliasWith === null ? [] : reachable(member, args, noAliasWith),
    ),
  };
}

function reachable(
  member: MemberSpec,
  args: unknown[],
  paramName: string,
): readonly object[] {
  const index = member.params.findIndex((param) => param.name === paramName);
  return index < 0
    ? []
    : traverse(args[index], (member.params[index] as ParamSpec).type);
}

export function serializeResult(
  member: MemberSpec,
  result: unknown,
  args: unknown[],
  watched: WatchedInputs,
): unknown {
  const { returns, params } = member;
  if (returns.outputFrom !== null) {
    const index = params.findIndex(
      (param) => param.name === returns.outputFrom,
    );
    return encode(args[index], (params[index] as ParamSpec).type);
  }
  if (returns.as === "value") {
    return encodeNodeValue(result, returns.type.text);
  }
  if (returns.as === "index") {
    return nodeIndex(result, watched.order, returns.of ?? "");
  }
  const output = encode(result, returns.type);
  if (
    returns.noAliasWith !== null &&
    traverse(result, returns.type).some((node) => watched.aliased.has(node))
  ) {
    throw new InvalidOutput(
      `the result shares nodes with ${returns.noAliasWith}; build new nodes instead`,
    );
  }
  return output;
}

function nodeIndex(
  result: unknown,
  order: readonly object[],
  ownerName: string,
): number {
  if (result === null) {
    return -1;
  }
  if (typeof result !== "object") {
    throw new InvalidOutput(
      `expected a node of "${ownerName}" or null, got ${describe(result)}`,
    );
  }
  const index = order.indexOf(result);
  if (index < 0) {
    throw new InvalidOutput(`the returned node is not a node of "${ownerName}"`);
  }
  return index;
}

/** Accumulates the time spent inside user calls only. */
export class Stopwatch {
  #elapsed = 0n;

  time<T>(call: () => T): T {
    const started = process.hrtime.bigint();
    try {
      return call();
    } finally {
      this.#elapsed += process.hrtime.bigint() - started;
    }
  }

  get nanoseconds(): number {
    return Number(this.#elapsed);
  }
}
