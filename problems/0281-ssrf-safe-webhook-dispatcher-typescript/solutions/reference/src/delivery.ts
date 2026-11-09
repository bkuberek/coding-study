// One delivery to one URL: up to MAX_ATTEMPTS attempts, each following redirects itself, so that
// every hop is checked the way the first one was.

import { setTimeout as sleep } from "node:timers/promises";

import { resolveDestination } from "./destinations.ts";
import {
  MAX_ATTEMPTS,
  MAX_REDIRECTS,
  MAX_RESPONSE_BYTES,
  REQUEST_TIMEOUT_MS,
  RETRY_WAIT_MS,
} from "./limits.ts";
import { originFor } from "./network.ts";
import { webhookUrl } from "./urls.ts";

export type DeliveryError =
  | "unresolvable_host"
  | "blocked_destination"
  | "invalid_redirect"
  | "too_many_redirects"
  | "timeout"
  | "connection_failed"
  | "response_too_large"
  | "bad_status";

/** How an attempt ended. `status` is that of the last answer it received, or null for none. */
export type Outcome =
  | { delivered: true; status: number }
  | { delivered: false; error: DeliveryError; status: number | null };

/** What every request of a delivery carries: the same body and headers, on every hop. */
export type Payload = { body: string; headers: Record<string, string> };

type Answer =
  | { status: number; location: string | null }
  | { error: "timeout" | "connection_failed" | "response_too_large"; status: number | null };

const REDIRECT_STATUSES: ReadonlySet<number> = new Set([301, 302, 303, 307, 308]);

export async function deliver(url: URL, payload: Payload): Promise<Outcome> {
  for (let attempt = 1; ; attempt += 1) {
    const outcome = await attemptDelivery(url, payload);
    if (attempt === MAX_ATTEMPTS || !worthRetrying(outcome)) {
      return outcome;
    }
    await sleep(RETRY_WAIT_MS);
  }
}

/** A timeout, a lost connection and a 5xx may pass. Anything else would answer the same again. */
export function worthRetrying(outcome: Outcome): boolean {
  if (outcome.delivered) {
    return false;
  }
  if (outcome.error === "timeout" || outcome.error === "connection_failed") {
    return true;
  }
  return outcome.error === "bad_status" && outcome.status !== null && outcome.status >= 500;
}

async function attemptDelivery(url: URL, payload: Payload): Promise<Outcome> {
  let hop = url;
  let lastStatus: number | null = null;
  for (let redirects = 0; ; redirects += 1) {
    const destination = await resolveDestination(hop);
    if ("refusal" in destination) {
      return { delivered: false, error: destination.refusal, status: lastStatus };
    }
    const answer = await send(destination.address, hop, payload);
    if ("error" in answer) {
      return { delivered: false, error: answer.error, status: answer.status ?? lastStatus };
    }
    const status = answer.status;
    lastStatus = status;
    if (!REDIRECT_STATUSES.has(status)) {
      return status >= 200 && status < 300
        ? { delivered: true, status }
        : { delivered: false, error: "bad_status", status };
    }
    if (redirects === MAX_REDIRECTS) {
      return { delivered: false, error: "too_many_redirects", status };
    }
    const next = answer.location === null ? null : webhookUrl(answer.location, hop);
    if (next === null) {
      return { delivered: false, error: "invalid_redirect", status };
    }
    hop = next;
  }
}

/** One request to the address already checked, never to the name, which could answer anew. */
async function send(address: string, url: URL, payload: Payload): Promise<Answer> {
  const signal = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(`${originFor(address)}${url.pathname}${url.search}`, {
      method: "POST",
      headers: payload.headers,
      body: payload.body,
      redirect: "manual",
      signal,
    });
  } catch {
    return { error: signal.aborted ? "timeout" : "connection_failed", status: null };
  }
  try {
    if (!(await bodyFits(response, MAX_RESPONSE_BYTES))) {
      return { error: "response_too_large", status: response.status };
    }
  } catch {
    return { error: signal.aborted ? "timeout" : "connection_failed", status: response.status };
  }
  return { status: response.status, location: response.headers.get("location") };
}

/** Reads the body up to `limit` bytes and no further: a body is only as big as you let it be. */
async function bodyFits(response: Response, limit: number): Promise<boolean> {
  if (response.body === null) {
    return true;
  }
  const reader = response.body.getReader();
  let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) {
      return true;
    }
    size += value.byteLength;
    if (size > limit) {
      await reader.cancel();
      return false;
    }
  }
}
