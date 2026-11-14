// Reading request bodies into what the service works with, or nothing when a field breaks its
// rule. Every rule here is from the statement's tables.

export const MAIN = "main";
const ORDER = /^[A-Za-z0-9_-]{1,64}$/;
const MAX_ITEMS = 10;
const MAX_QUANTITY = 100;
const MAX_RECEIPT = 1000;
const MAX_HOLD_SECONDS = 3600;
const DEFAULT_HOLD_SECONDS = 900;

export type Item = { sku: string; quantity: number; warehouse: string };
export type ReservationRequest = { order: string; items: Item[]; holdSeconds: number };
export type Receipt = { sku: string; quantity: number };

type Fields = Record<string, unknown>;

function isObject(value: unknown): value is Fields {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isWholeIn(value: unknown, low: number, high: number): value is number {
  return Number.isInteger(value) && (value as number) >= low && (value as number) <= high;
}

function isName(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

function item(value: unknown): Item | undefined {
  if (!isObject(value) || !isName(value.sku) || !isWholeIn(value.quantity, 1, MAX_QUANTITY)) {
    return undefined;
  }
  const warehouse = value.warehouse ?? MAIN;
  if (!isName(warehouse)) {
    return undefined;
  }
  return { sku: value.sku, quantity: value.quantity, warehouse };
}

export function reservationRequest(body: unknown): ReservationRequest | undefined {
  if (!isObject(body) || typeof body.order !== "string" || !ORDER.test(body.order)) {
    return undefined;
  }
  const { items } = body;
  if (!Array.isArray(items) || items.length === 0 || items.length > MAX_ITEMS) {
    return undefined;
  }
  const read = items.map(item);
  if (read.some((one) => one === undefined)) {
    return undefined;
  }
  const checked = read as Item[];
  if (new Set(checked.map((one) => one.sku)).size !== checked.length) {
    return undefined;
  }
  const holdSeconds = body.hold_seconds ?? DEFAULT_HOLD_SECONDS;
  if (!isWholeIn(holdSeconds, 0, MAX_HOLD_SECONDS)) {
    return undefined;
  }
  return { order: body.order, items: checked, holdSeconds };
}

export function receipt(body: unknown): Receipt | undefined {
  if (!isObject(body) || !isName(body.sku) || !isWholeIn(body.quantity, 1, MAX_RECEIPT)) {
    return undefined;
  }
  return { sku: body.sku, quantity: body.quantity };
}
