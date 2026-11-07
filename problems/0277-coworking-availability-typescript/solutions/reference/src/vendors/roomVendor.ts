// The vendor of the main building's rooms: what it speaks, and when it is worth asking again.

import { getWithinLimit, isObject, sleep } from "./roomSource.ts";
import type { RoomSource, Slot } from "./roomSource.ts";

const NAME = "room-vendor";
const MAX_REQUESTS = 3;
const RETRY_WAIT_MS = 200;
const MS_PER_SECOND = 1000;

/** How long to wait before asking again; null when asking again will not help. */
export function waitBeforeRetry(status: number, retryAfter: string | null): number | null {
  if (status === 429 && retryAfter !== null && /^\d+$/.test(retryAfter)) {
    return Number(retryAfter) * MS_PER_SECOND;
  }
  return status === 429 || status >= 500 ? RETRY_WAIT_MS : null;
}

function slotsIn(body: unknown): Slot[] {
  if (!isObject(body) || !Array.isArray(body.rooms)) {
    throw new Error(`${NAME} sent no rooms`);
  }
  return body.rooms.flatMap((room: { id: string; slots: unknown[] }) =>
    (room.slots as { start: string; end: string; status: string }[])
      .filter((slot) => slot.status === "open")
      .map((slot) => ({ room: room.id, start: slot.start, end: slot.end, vendor: NAME })),
  );
}

export class RoomVendorClient implements RoomSource {
  readonly name = NAME;
  readonly #url: string;

  constructor(url: string) {
    this.#url = url;
  }

  async openSlots(date: string): Promise<Slot[]> {
    const url = `${this.#url}/v1/rooms/availability?date=${date}`;
    let answer = await getWithinLimit(url);
    for (let sent = 1; sent < MAX_REQUESTS; sent += 1) {
      const wait = waitBeforeRetry(answer.status, answer.headers.get("retry-after"));
      if (wait === null) {
        break;
      }
      await answer.body?.cancel();
      await sleep(wait);
      answer = await getWithinLimit(url);
    }
    if (!answer.ok) {
      throw new Error(`${NAME} answered ${answer.status}`);
    }
    return slotsIn(await answer.json());
  }
}
