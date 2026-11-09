// What the provider sends: one payment event per delivery, as vendors/payment-provider/API.md
// describes it. An event keeps every field it came with, so two of them compare whole.

export type PaymentEvent = Readonly<Record<string, unknown>> & {
  readonly id: string;
  readonly type: string;
  readonly order: string;
  readonly sequence: number;
};

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isName(value: unknown): value is string {
  return typeof value === "string" && value !== "";
}

/** The event a JSON value describes; null when it is not one. */
export function eventFrom(value: unknown): PaymentEvent | null {
  if (!isObject(value) || !isName(value.id) || !isName(value.type) || !isName(value.order)) {
    return null;
  }
  if (!Number.isInteger(value.sequence) || Number(value.sequence) < 1) {
    return null;
  }
  return value as PaymentEvent;
}

/** The event a delivery's body holds; null when it holds none. */
export function parseEvent(body: string): PaymentEvent | null {
  try {
    return eventFrom(JSON.parse(body));
  } catch {
    return null;
  }
}
