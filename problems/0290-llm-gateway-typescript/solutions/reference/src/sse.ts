// Server-sent events from a provider's body, each as soon as it has arrived.

import { ENDED_EARLY, ProviderFailure, STALLED } from "./provider.ts";

/** The longest a stream may go without sending anything, before its first event or between two. */
export const SILENCE_LIMIT_MS = 1000;

export type ServerSentEvent = { event: string; data: string };

const EVENT_END = "\n\n";
const UNNAMED = "message";

/** One event's lines: `event:` names it, and its `data:` lines join with newlines. */
export function parseEvent(block: string): ServerSentEvent {
  let event = UNNAMED;
  const data: string[] = [];
  for (const line of block.split("\n")) {
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    const value = colon === -1 ? "" : line.slice(colon + 1).replace(/^ /, "");
    if (field === "event") {
      event = value;
    } else if (field === "data") {
      data.push(value);
    }
  }
  return { event, data: data.join("\n") };
}

/** Each event of `body` once its blank line has arrived: one read can hold half an event, or
 * several. Throws a ProviderFailure when the stream goes quiet for SILENCE_LIMIT_MS or its
 * connection fails, and returns when the provider closes it. */
export async function* serverSentEvents(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<ServerSentEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let pending = "";
  try {
    for (;;) {
      const read = await withinSilence(reader.read());
      if (read.done) {
        return;
      }
      pending += decoder.decode(read.value, { stream: true });
      let end = pending.indexOf(EVENT_END);
      while (end !== -1) {
        yield parseEvent(pending.slice(0, end));
        pending = pending.slice(end + EVENT_END.length);
        end = pending.indexOf(EVENT_END);
      }
    }
  } finally {
    reader.cancel().catch(() => undefined);
  }
}

async function withinSilence<T>(read: Promise<T>): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const silence = new Promise<never>((_resolve, reject) => {
    timer = setTimeout(() => reject(new ProviderFailure(STALLED)), SILENCE_LIMIT_MS);
  });
  try {
    return await Promise.race([read, silence]);
  } catch (error) {
    throw error instanceof ProviderFailure ? error : new ProviderFailure(ENDED_EARLY);
  } finally {
    clearTimeout(timer);
  }
}
