// The runner wire format (docs/specs/runners.md): the request file the CLI writes and the JSON
// Lines events this runner appends to `--out`, one synchronous write per event.

import { readFileSync, openSync, writeSync } from "node:fs";
import { Buffer } from "node:buffer";
import { parseType, UnknownTypeError, type TypeSpec } from "./types.ts";

export const PROTOCOL_VERSION = 1;
const TEST_MODE = "test";
const CONCURRENT_KIND = "concurrent";
const SUITE_KIND = "suite";
/** The one test framework this runner hosts in a suite job. */
const NODE_TEST_FRAMEWORK = "node-test";
const ASYNC_MODEL = "async";
const BENCH_MODE = "bench";
const NANOSECONDS_PER_MILLISECOND = 1_000_000;

/** A request this runner cannot execute; the runner exits with code 2 before any case. */
export class BadRequest extends Error {}

export interface ParamSpec {
  readonly name: string;
  readonly type: TypeSpec;
  readonly refOf: string | null;
}

export interface ReturnSpec {
  readonly type: TypeSpec;
  readonly outputFrom: string | null;
  readonly as: "value" | "index" | null;
  readonly of: string | null;
  readonly noAliasWith: string | null;
}

/** A function, a method, or a constructor (which returns `void`). */
export interface MemberSpec {
  readonly name: string;
  readonly params: readonly ParamSpec[];
  readonly returns: ReturnSpec;
}

export interface FunctionCase {
  readonly id: string;
  readonly input: Readonly<Record<string, unknown>>;
}

export interface OperationCase {
  readonly id: string;
  readonly ops: readonly string[];
  readonly args: readonly (readonly unknown[])[];
}

export interface FunctionJob {
  readonly shape: "function";
  readonly jobId: string;
  readonly path: string;
  readonly exportName: string;
  readonly member: MemberSpec;
  readonly cases: readonly FunctionCase[];
}

export interface MethodSpec {
  /** The method's name in TypeScript (`names.methods`); `member.name` is canonical. */
  readonly memberName: string;
  readonly member: MemberSpec;
}

export interface ClassJob {
  readonly shape: "class";
  readonly jobId: string;
  readonly path: string;
  readonly exportName: string;
  readonly constructorSpec: MemberSpec;
  /** Keyed by canonical method name, as operations name them. */
  readonly methods: ReadonlyMap<string, MethodSpec>;
  readonly cases: readonly OperationCase[];
}

export type Job = FunctionJob | ClassJob;

/** Ops with their arguments; worker and final scripts have no constructor. */
export interface Script {
  readonly ops: readonly string[];
  readonly args: readonly (readonly unknown[])[];
}

export interface Perturbation {
  readonly yieldProbability: number;
  readonly maxYields: number;
}

/** One stress run of a concurrent job (docs/specs/runners.md#request). */
export interface StressCase {
  readonly id: string;
  /** Already the case's seed plus the run index. */
  readonly seed: number;
  readonly deadlineMs: number;
  readonly perturb: Perturbation;
  readonly setup: Script;
  readonly workers: readonly Script[];
  readonly final: Script | null;
}

/** A concurrent job: sequential cases, then stress runs; TypeScript runs the async model only. */
export interface ConcurrentJob {
  readonly shape: "concurrent";
  readonly jobId: string;
  readonly path: string;
  /** The class as a design job without cases, so it loads like one. */
  readonly design: ClassJob;
  readonly cases: readonly (OperationCase | StressCase)[];
}

/** A project's own `node:test` files, discovered from its root (docs/specs/runners.md#suite-job). */
export interface SuiteJob {
  readonly shape: "suite";
  readonly jobId: string;
  readonly root: string;
  /** Files, relative to the root, that are not run. */
  readonly exclude: readonly string[];
  /** Test ids, or their last part, to run; empty: every test. */
  readonly select: readonly string[];
  /** Test ids not to run: those reported before a restart, and the one that hung or crashed. */
  readonly skip: readonly string[];
}

export type TestJob = Job | ConcurrentJob | SuiteJob;

export interface ErrorInfo {
  readonly type: string;
  readonly message: string;
  readonly trace?: string;
}

export type CaseStatus =
  | { readonly status: "ok"; readonly output: unknown }
  | {
      readonly status: "error";
      readonly error: ErrorInfo;
      readonly op_index?: number;
      readonly partial_output?: readonly unknown[];
    }
  | { readonly status: "invalid_output"; readonly reason: string };

export type BenchCase = FunctionCase | OperationCase;

export interface BenchTarget {
  readonly targetId: string;
  readonly job: Job;
  /** `output: true`: report each size's check call output (`bench_output`). */
  readonly emitsOutput: boolean;
}

export interface BenchInput {
  readonly size: number;
  readonly testCase: BenchCase;
  /** At most this many calls, each on a fresh copy of the input, per timed sample. */
  readonly maxBatch: number;
}

export interface BenchSettings {
  readonly reps: number;
  readonly warmup: { readonly min: number; readonly max: number; readonly cv: number };
  readonly budgetNs: number;
  readonly memory: boolean;
  readonly minSampleNs: number;
}

export interface BenchJob {
  readonly jobId: string;
  readonly targets: readonly BenchTarget[];
  readonly inputs: readonly BenchInput[];
  readonly settings: BenchSettings;
}

export type Request =
  | { readonly mode: "test"; readonly jobs: readonly TestJob[] }
  | { readonly mode: "bench"; readonly jobs: readonly BenchJob[] };

export function readRequest(path: string): Request {
  const root = object(parseJsonFile(path), "request");
  if (field(root, "protocol") !== PROTOCOL_VERSION) {
    const protocol = JSON.stringify(field(root, "protocol"));
    throw new BadRequest(
      `protocol ${protocol} is not supported; this runner speaks ${PROTOCOL_VERSION}`,
    );
  }
  const jobs = array(root, "jobs", "request").map((job, index) =>
    object(job, `jobs[${index}]`),
  );
  const mode = field(root, "mode");
  if (mode === TEST_MODE) {
    return { mode: "test", jobs: jobs.map(parseTestJob) };
  }
  if (mode === BENCH_MODE) {
    return { mode: "bench", jobs: jobs.map(parseBenchJob) };
  }
  throw new BadRequest(`mode ${JSON.stringify(mode)} is not supported`);
}

export class EventWriter {
  readonly #descriptor: number;

  constructor(path: string) {
    this.#descriptor = openSync(path, "w");
  }

  write(event: Readonly<Record<string, unknown>>): void {
    const bytes = Buffer.from(`${JSON.stringify(event)}\n`, "utf8");
    let written = 0;
    while (written < bytes.length) {
      written += writeSync(this.#descriptor, bytes, written);
    }
  }
}

function parseJsonFile(path: string): unknown {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    throw new BadRequest(`cannot read the request ${path}: ${String(error)}`);
  }
}

function parseTestJob(job: Record<string, unknown>): TestJob {
  const kind = field(job, "kind");
  if (kind === SUITE_KIND) {
    return suiteJob(job);
  }
  if (kind !== CONCURRENT_KIND) {
    return parseJob(job);
  }
  const jobId = string(job, "job_id", "job");
  const where = `job "${jobId}"`;
  if (field(job, "model") !== ASYNC_MODEL) {
    throw new BadRequest(
      `${where}: TypeScript runs only the async model, not ${JSON.stringify(field(job, "model"))}`,
    );
  }
  const cases = array(job, "cases", where).map((value, index) =>
    object(value, `${where} cases[${index}]`),
  );
  const design = parseJob({ ...job, cases: [] });
  if (design.shape !== "class") {
    throw new BadRequest(`${where}: a concurrent job needs a class signature`);
  }
  return {
    shape: "concurrent",
    jobId,
    path: design.path,
    design,
    cases: cases.map((value) => {
      const id = string(value, "id", where);
      const stress = field(value, "stress");
      return stress === undefined
        ? operationCase(value, id, where)
        : stressCase(object(stress, `${where} ${id} stress`), id, where);
    }),
  };
}

function suiteJob(job: Record<string, unknown>): SuiteJob {
  const jobId = string(job, "job_id", "job");
  const where = `job "${jobId}"`;
  const framework = string(job, "framework", where);
  if (framework !== NODE_TEST_FRAMEWORK) {
    throw new BadRequest(`${where}: framework "${framework}" is not supported`);
  }
  return {
    shape: "suite",
    jobId,
    root: string(job, "root", where),
    exclude: strings(job, "exclude", where),
    select: strings(job, "select", where),
    skip: strings(job, "skip", where),
  };
}

function stressCase(
  stress: Record<string, unknown>,
  id: string,
  where: string,
): StressCase {
  const perturb = object(field(stress, "perturb"), `${where} perturb`);
  const final = field(stress, "final");
  return {
    id,
    seed: integer(stress, "seed", where),
    deadlineMs: integer(stress, "deadline_ms", where),
    perturb: {
      yieldProbability: numberValue(
        field(perturb, "yield_probability"),
        `${where} yield_probability`,
      ),
      maxYields: integer(perturb, "max_yields", where),
    },
    setup: script(object(field(stress, "setup"), `${where} setup`), where),
    workers: array(stress, "workers", where).map((worker) =>
      script(object(worker, `${where} worker`), where),
    ),
    final: final === undefined ? null : script(object(final, `${where} final`), where),
  };
}

function script(value: Record<string, unknown>, where: string): Script {
  const { ops, args } = operationCase(value, "", where);
  if (ops.length !== args.length) {
    throw new BadRequest(`${where}: a script needs one argument array per op`);
  }
  return { ops, args };
}

function parseJob(job: Record<string, unknown>): Job {
  const jobId = string(job, "job_id", "job");
  const where = `job "${jobId}"`;
  const path = string(
    object(field(job, "target"), `${where} target`),
    "path",
    `${where} target`,
  );
  const names = object(field(job, "names"), `${where} names`);
  const signature = object(field(job, "signature"), `${where} signature`);
  const cases = array(job, "cases", where).map((value, index) =>
    object(value, `${where} cases[${index}]`),
  );
  if (field(signature, "function") !== undefined) {
    return {
      shape: "function",
      jobId,
      path,
      exportName: string(names, "function", `${where} names`),
      member: parseMember(
        object(field(signature, "function"), `${where} signature`),
        where,
      ),
      cases: cases.map((value) => ({
        id: string(value, "id", where),
        input: object(field(value, "input"), `${where} case input`),
      })),
    };
  }
  const declared = object(field(signature, "class"), `${where} signature`);
  const exportName = string(names, "class", `${where} names`);
  const memberNames = object(field(names, "methods"), `${where} names.methods`);
  const constructorParams = object(
    field(declared, "constructor"),
    `${where} constructor`,
  );
  return {
    shape: "class",
    jobId,
    path,
    exportName,
    constructorSpec: {
      name: exportName,
      params: parseParams(constructorParams, where),
      returns: voidReturn(),
    },
    methods: new Map(
      array(declared, "methods", where).map((value) => {
        const member = parseMember(object(value, `${where} method`), where);
        return [
          member.name,
          {
            memberName: string(
              memberNames,
              member.name,
              `${where} names.methods`,
            ),
            member,
          },
        ];
      }),
    ),
    cases: cases.map((value) =>
      operationCase(value, string(value, "id", where), where),
    ),
  };
}

function operationCase(
  value: Record<string, unknown>,
  id: string,
  where: string,
): OperationCase {
  return {
    id,
    ops: array(value, "ops", where).map((op) =>
      stringValue(op, `${where} ops`),
    ),
    args: array(value, "args", where).map((args) =>
      arrayValue(args, `${where} args`),
    ),
  };
}

/** Each target parses as a test job without cases, so it loads like one. */
function parseBenchJob(job: Record<string, unknown>): BenchJob {
  const jobId = string(job, "job_id", "bench job");
  const where = `bench job "${jobId}"`;
  const signature = object(field(job, "signature"), `${where} signature`);
  const targets = array(job, "targets", where).map((value, index) => {
    const target = object(value, `${where} targets[${index}]`);
    const targetId = string(target, "target_id", where);
    const parsed = parseJob({
      job_id: `${jobId}/${targetId}`,
      target: field(target, "target"),
      names: field(target, "names"),
      signature,
      cases: [],
    });
    return { targetId, job: parsed, emitsOutput: field(target, "output") === true };
  });
  const functionKind = field(signature, "function") !== undefined;
  const inputs = array(job, "inputs", where).map((value, index) => {
    const input = object(value, `${where} inputs[${index}]`);
    const size = integer(input, "size", where);
    const id = `n=${size}`;
    const testCase: BenchCase = functionKind
      ? { id, input: object(field(input, "input"), `${where} input`) }
      : operationCase(input, id, where);
    return { size, testCase, maxBatch: integer(input, "max_batch", where) };
  });
  return { jobId, targets, inputs, settings: parseSettings(job, where) };
}

function parseSettings(
  job: Record<string, unknown>,
  where: string,
): BenchSettings {
  const settings = object(field(job, "settings"), `${where} settings`);
  const warmup = object(field(settings, "warmup"), `${where} warmup`);
  const memory = field(settings, "memory");
  if (typeof memory !== "boolean") {
    throw new BadRequest(`${where} settings.memory must be true or false`);
  }
  return {
    reps: integer(settings, "reps", where),
    warmup: {
      min: integer(warmup, "min", where),
      max: integer(warmup, "max", where),
      cv: numberValue(field(warmup, "cv"), `${where} warmup.cv`),
    },
    budgetNs: integer(settings, "budget_ms", where) * NANOSECONDS_PER_MILLISECOND,
    memory,
    minSampleNs: integer(settings, "min_sample_ns", where),
  };
}

function integer(
  owner: Record<string, unknown>,
  key: string,
  where: string,
): number {
  const value = numberValue(field(owner, key), `${where} "${key}"`);
  if (!Number.isInteger(value)) {
    throw new BadRequest(`${where} "${key}" must be an integer`);
  }
  return value;
}

function numberValue(value: unknown, where: string): number {
  if (typeof value !== "number") {
    throw new BadRequest(`${where} must be a number`);
  }
  return value;
}

function parseMember(
  member: Record<string, unknown>,
  where: string,
): MemberSpec {
  const returns = object(field(member, "returns"), `${where} returns`);
  return {
    name: string(member, "name", where),
    params: parseParams(member, where),
    returns: {
      type: typeOf(returns, where),
      outputFrom: optionalString(returns, "output_from", where),
      as: serializeAs(optionalString(returns, "as", where), where),
      of: optionalString(returns, "of", where),
      noAliasWith: optionalString(returns, "no_alias_with", where),
    },
  };
}

function parseParams(
  owner: Record<string, unknown>,
  where: string,
): readonly ParamSpec[] {
  return array(owner, "params", where).map((value) => {
    const param = object(value, `${where} param`);
    return {
      name: string(param, "name", where),
      type: typeOf(param, where),
      refOf: optionalString(param, "ref_of", where),
    };
  });
}

function typeOf(owner: Record<string, unknown>, where: string): TypeSpec {
  try {
    return parseType(string(owner, "type", where));
  } catch (error) {
    if (error instanceof UnknownTypeError) {
      throw new BadRequest(`${where}: ${error.message}`);
    }
    throw error;
  }
}

function serializeAs(value: string | null, where: string): ReturnSpec["as"] {
  if (value === null || value === "value" || value === "index") {
    return value;
  }
  throw new BadRequest(`${where}: unknown "as" modifier "${value}"`);
}

function voidReturn(): ReturnSpec {
  return {
    type: parseType("void"),
    outputFrom: null,
    as: null,
    of: null,
    noAliasWith: null,
  };
}

function object(value: unknown, where: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new BadRequest(`${where} must be an object`);
  }
  return value as Record<string, unknown>;
}

/** An own property only, so names such as "constructor" never reach `Object.prototype`. */
function field(owner: Record<string, unknown>, key: string): unknown {
  return Object.hasOwn(owner, key) ? owner[key] : undefined;
}

function array(
  owner: Record<string, unknown>,
  key: string,
  where: string,
): readonly unknown[] {
  return arrayValue(field(owner, key), `${where} "${key}"`);
}

function arrayValue(value: unknown, where: string): readonly unknown[] {
  if (!Array.isArray(value)) {
    throw new BadRequest(`${where} must be an array`);
  }
  return value;
}

function string(
  owner: Record<string, unknown>,
  key: string,
  where: string,
): string {
  return stringValue(field(owner, key), `${where} "${key}"`);
}

function strings(
  owner: Record<string, unknown>,
  key: string,
  where: string,
): readonly string[] {
  return array(owner, key, where).map((value) =>
    stringValue(value, `${where} "${key}"`),
  );
}

function optionalString(
  owner: Record<string, unknown>,
  key: string,
  where: string,
): string | null {
  return field(owner, key) === undefined ? null : string(owner, key, where);
}

function stringValue(value: unknown, where: string): string {
  if (typeof value !== "string") {
    throw new BadRequest(`${where} must be a string`);
  }
  return value;
}
