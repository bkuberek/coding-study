// Reading request bodies into what the service works with, or nothing when a field breaks its
// rule. Every rule here is from the statement's tables.

const NAME = /^[A-Za-z0-9_-]{1,64}$/;
const QUEUE = /^[a-z0-9-]{1,32}$/;
const MAX_ERROR_LENGTH = 200;
const MAX_SECONDS = 3600;
const DEFAULT_VISIBILITY_SECONDS = 30;
const MAX_ATTEMPTS = 10;
const DEFAULT_MAX_ATTEMPTS = 3;
const DEFAULT_BACKOFF_SECONDS = 30;
const MAX_PRIORITY = 9;
const DEFAULT_PRIORITY = 5;

export type NewJob = {
  id: string;
  tenant: string;
  payload: Fields;
  maxAttempts: number;
  backoffSeconds: number;
  priority: number;
};
export type Failure = { attempt: number; error: string };

type Fields = Record<string, unknown>;

function isObject(value: unknown): value is Fields {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isName(value: unknown): value is string {
  return typeof value === "string" && NAME.test(value);
}

function isWholeIn(value: unknown, low: number, high: number): value is number {
  return Number.isInteger(value) && (value as number) >= low && (value as number) <= high;
}

// A whole number within its range, its default when left out, or nothing when it breaks the rule.
function wholeOr(value: unknown, fallback: number, high: number, low = 0): number | undefined {
  const read = value ?? fallback;
  return isWholeIn(read, low, high) ? read : undefined;
}

export function isQueue(value: string): boolean {
  return QUEUE.test(value);
}

export function newJob(body: unknown): NewJob | undefined {
  if (!isObject(body) || !isName(body.id) || !isName(body.tenant) || !isObject(body.payload)) {
    return undefined;
  }
  const maxAttempts = wholeOr(body.max_attempts, DEFAULT_MAX_ATTEMPTS, MAX_ATTEMPTS, 1);
  const backoffSeconds = wholeOr(body.backoff_seconds, DEFAULT_BACKOFF_SECONDS, MAX_SECONDS);
  const priority = wholeOr(body.priority, DEFAULT_PRIORITY, MAX_PRIORITY);
  if (maxAttempts === undefined || backoffSeconds === undefined || priority === undefined) {
    return undefined;
  }
  const { id, tenant, payload } = body;
  return { id, tenant, payload, maxAttempts, backoffSeconds, priority };
}

export function visibilitySeconds(body: unknown): number | undefined {
  if (!isObject(body)) {
    return undefined;
  }
  return wholeOr(body.visibility_seconds, DEFAULT_VISIBILITY_SECONDS, MAX_SECONDS);
}

export function attempt(body: unknown): number | undefined {
  return isObject(body) && isWholeIn(body.attempt, 1, Number.MAX_SAFE_INTEGER)
    ? body.attempt
    : undefined;
}

export function failure(body: unknown): Failure | undefined {
  const tried = attempt(body);
  if (tried === undefined || !isObject(body) || typeof body.error !== "string") {
    return undefined;
  }
  const { error } = body;
  return error.length === 0 || error.length > MAX_ERROR_LENGTH ? undefined : { attempt: tried, error };
}
