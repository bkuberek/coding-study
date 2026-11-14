// One request to a provider, within the gateway's limit on how long it waits for an answer to start.

import { MALFORMED, NOT_ANSWERED, ProviderFailure, isObject } from "./provider.ts";

/** The longest a provider gets to send its status and headers, and to finish a whole answer. */
export const ANSWER_LIMIT_MS = 1500;

export type Post = {
  url: string;
  headers: Record<string, string>;
  body: unknown;
  signal: AbortSignal;
};

/** A request whose status and headers came in time. Its clock still runs: a whole answer reads
 * its body before stopping it, and a stream stops it at once and times its silences instead. */
export type Attempt = { response: Response; stopClock(): void };

export async function send(post: Post): Promise<Attempt> {
  const clock = new AbortController();
  const timer = setTimeout(() => clock.abort(), ANSWER_LIMIT_MS);
  const stopClock = () => clearTimeout(timer);
  try {
    const response = await fetch(post.url, {
      method: "POST",
      headers: { ...post.headers, "Content-Type": "application/json" },
      body: JSON.stringify(post.body),
      signal: AbortSignal.any([clock.signal, post.signal]),
    });
    return { response, stopClock };
  } catch {
    stopClock();
    throw new ProviderFailure(NOT_ANSWERED);
  }
}

/** The JSON object of a whole answer, read before the clock runs out. */
export async function wholeBody(attempt: Attempt): Promise<Record<string, unknown>> {
  let body: unknown;
  try {
    body = await attempt.response.json();
  } catch {
    throw new ProviderFailure(NOT_ANSWERED);
  } finally {
    attempt.stopClock();
  }
  if (!isObject(body)) {
    throw new ProviderFailure(MALFORMED);
  }
  return body;
}

/** Drops an answer the gateway will not use, so its connection is not left open. */
export async function discard(attempt: Attempt): Promise<void> {
  attempt.stopClock();
  await attempt.response.body?.cancel();
}

/** The body of a stream, whose silences the reader times from here on. */
export function streamBody(attempt: Attempt): ReadableStream<Uint8Array> {
  attempt.stopClock();
  const { body } = attempt.response;
  if (body === null) {
    throw new ProviderFailure(NOT_ANSWERED);
  }
  return body;
}
