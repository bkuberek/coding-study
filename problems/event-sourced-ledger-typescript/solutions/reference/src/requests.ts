// Reading requests into what the service works with, or nothing when a field breaks its rule.
// Every rule here is from the statement's tables.

const ID = /^[A-Za-z0-9_-]{1,64}$/;
const MAX_AMOUNT = 1_000_000;
const TIME = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;

export type Movement = { account: string; amount: number; expectedVersion?: number; eventId?: string };
export type Transfer = { from: string; to: string; amount: number; eventId?: string };

type Fields = Record<string, unknown>;

function isObject(value: unknown): value is Fields {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isId(value: unknown): value is string {
  return typeof value === "string" && ID.test(value);
}

function isAmount(value: unknown): value is number {
  return Number.isInteger(value) && (value as number) >= 1 && (value as number) <= MAX_AMOUNT;
}

function isVersion(value: unknown): value is number {
  return Number.isInteger(value) && (value as number) >= 0;
}

// An optional field: left out is fine, and given it must pass its check.
function isAbsentOr(value: unknown, check: (value: unknown) => boolean): boolean {
  return value === undefined || check(value);
}

// A deposit or a withdrawal on one account.
export function movement(account: string, body: unknown): Movement | undefined {
  if (!isId(account) || !isObject(body) || !isAmount(body.amount)) {
    return undefined;
  }
  if (!isAbsentOr(body.expected_version, isVersion) || !isAbsentOr(body.event_id, isId)) {
    return undefined;
  }
  return {
    account,
    amount: body.amount,
    expectedVersion: body.expected_version as number | undefined,
    eventId: body.event_id as string | undefined,
  };
}

export function transfer(body: unknown): Transfer | undefined {
  if (!isObject(body) || !isId(body.from) || !isId(body.to) || body.from === body.to) {
    return undefined;
  }
  if (!isAmount(body.amount) || !isAbsentOr(body.event_id, isId)) {
    return undefined;
  }
  return {
    from: body.from,
    to: body.to,
    amount: body.amount,
    eventId: body.event_id as string | undefined,
  };
}

// A time with its offset, such as `2026-02-15T00:00:00Z`, or nothing. `Date` alone would take a
// date with no time, read a time with no offset in the machine's own zone, and roll 30 February
// over to 2 March, so the shape and the fields are checked before it reads the text.
export function instant(text: string): Date | undefined {
  const parts = TIME.exec(text);
  if (parts === null) {
    return undefined;
  }
  const written = parts.slice(1, 7).map(Number);
  const [year, month, day, hour, minute, second] = written;
  const asWritten = new Date(Date.UTC(year, month - 1, day, hour, minute, second));
  const readBack = [
    asWritten.getUTCFullYear(),
    asWritten.getUTCMonth() + 1,
    asWritten.getUTCDate(),
    asWritten.getUTCHours(),
    asWritten.getUTCMinutes(),
    asWritten.getUTCSeconds(),
  ];
  const moment = new Date(text);
  const exists = readBack.every((field, index) => field === written[index]);
  return exists && !Number.isNaN(moment.getTime()) ? moment : undefined;
}
