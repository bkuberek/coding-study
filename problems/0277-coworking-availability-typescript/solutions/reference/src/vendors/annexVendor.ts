// The vendor of the building next door. It says most of what it means in the body of a 200.

import { getWithinLimit, isObject, sleep } from "./roomSource.ts";
import type { RoomSource, Slot } from "./roomSource.ts";

const NAME = "annex-vendor";
const BUSY = "BUSY";
const MINUTES_PER_HOUR = 60;

function clock(minutes: number): string {
  const hours = Math.floor(minutes / MINUTES_PER_HOUR);
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${pad(hours)}:${pad(minutes % MINUTES_PER_HOUR)}`;
}

function slotsIn(result: unknown): Slot[] {
  if (!isObject(result) || !Array.isArray(result.spaces)) {
    throw new Error(`${NAME} sent no spaces`);
  }
  return result.spaces.flatMap(
    (space: { code: string; open: { from_minute: number; minutes: number }[] }) =>
      space.open.map((window) => ({
        room: space.code,
        start: clock(window.from_minute),
        end: clock(window.from_minute + window.minutes),
        vendor: NAME,
      })),
  );
}

/** How long it asks you to wait before asking again; null when it asks for no such thing. */
function busyForMs(body: Record<string, unknown>): number | null {
  const error = body.error;
  if (!isObject(error) || error.code !== BUSY || typeof error.retry_after_ms !== "number") {
    return null;
  }
  return error.retry_after_ms;
}

export class AnnexVendorClient implements RoomSource {
  readonly name = NAME;
  readonly #url: string;

  constructor(url: string) {
    this.#url = url;
  }

  async openSlots(date: string): Promise<Slot[]> {
    const url = `${this.#url}/v2/spaces/open?day=${date.replaceAll("-", "")}`;
    const first = await this.#body(url);
    const wait = busyForMs(first);
    if (wait === null) {
      return this.#slots(first);
    }
    await sleep(wait);
    return this.#slots(await this.#body(url));
  }

  async #body(url: string): Promise<Record<string, unknown>> {
    const answer = await getWithinLimit(url);
    if (!answer.ok) {
      throw new Error(`${NAME} answered ${answer.status}`);
    }
    const body: unknown = await answer.json();
    if (!isObject(body)) {
      throw new Error(`${NAME} sent no object`);
    }
    return body;
  }

  #slots(body: Record<string, unknown>): Slot[] {
    if (body.ok !== true) {
      throw new Error(`${NAME} declined to answer`);
    }
    return slotsIn(body.result);
  }
}
