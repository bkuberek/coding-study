// The seam between the API and its vendors: every vendor, whatever it speaks, looks like this.

export type Slot = { room: string; start: string; end: string; vendor: string };

export interface RoomSource {
  readonly name: string;
  /** What can be booked on `date`, written YYYY-MM-DD. Rejects when the vendor gives no usable answer. */
  openSlots(date: string): Promise<Slot[]>;
}

/** The longest any vendor gets to answer one request. */
export const REQUEST_LIMIT_MS = 1500;

export function getWithinLimit(url: string): Promise<Response> {
  return fetch(url, { signal: AbortSignal.timeout(REQUEST_LIMIT_MS) });
}

export function sleep(ms: number): Promise<void> {
  return new Promise((done) => setTimeout(done, ms));
}

export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
