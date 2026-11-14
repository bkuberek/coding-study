// What the broker hands us, read defensively: anyone can put anything on a queue.

export interface Delivery {
  messageId: string;
  documentId: string;
  revision: number;
  pipelineVersion: number;
  body: string;
  deliveryCount: number;
}

/** A delivery that does not parse, or whose fields are not what `Delivery` says. */
export class MalformedDelivery extends Error {
  constructor(reason: string) {
    super(`malformed delivery: ${reason}`);
    this.name = "MalformedDelivery";
  }
}

function positiveWhole(fields: Record<string, unknown>, name: string): number {
  const value = fields[name];
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1) {
    throw new MalformedDelivery(`${name} must be a whole number from 1`);
  }
  return value;
}

function nonEmptyText(fields: Record<string, unknown>, name: string): string {
  const value = fields[name];
  if (typeof value !== "string" || value === "") {
    throw new MalformedDelivery(`${name} must be non-empty text`);
  }
  return value;
}

export function parseDelivery(text: string): Delivery {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new MalformedDelivery("not JSON");
  }
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new MalformedDelivery("not a JSON object");
  }
  const fields = parsed as Record<string, unknown>;
  return {
    messageId: nonEmptyText(fields, "messageId"),
    documentId: nonEmptyText(fields, "documentId"),
    revision: positiveWhole(fields, "revision"),
    pipelineVersion: positiveWhole(fields, "pipelineVersion"),
    body: nonEmptyText(fields, "body"),
    deliveryCount: positiveWhole(fields, "deliveryCount"),
  };
}
