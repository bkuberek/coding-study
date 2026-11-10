// The primary provider: a chat-completions-style API, and when it is worth asking again.

import { setTimeout as sleep } from "node:timers/promises";

import { ENDED_EARLY, MALFORMED, ProviderFailure, isObject, providerJson, usageOf } from "./provider.ts";
import type { Answer, Ask, Piece, Provider, Usage } from "./provider.ts";
import { serverSentEvents } from "./sse.ts";
import { discard, send, streamBody, wholeBody } from "./upstream.ts";
import type { Attempt } from "./upstream.ts";

const MAX_REQUESTS = 3;
const LONGEST_WAIT_S = 2;
const WAIT_WITHOUT_RETRY_AFTER_MS = 500;
const MS_PER_SECOND = 1000;
const TOO_MANY_REQUESTS = 429;
const END_OF_STREAM = "[DONE]";

/** How long to wait before asking again; null when asking again is not worth the caller's wait. */
export function waitBeforeRetry(status: number, retryAfter: string | null): number | null {
  if (status !== TOO_MANY_REQUESTS) {
    return null;
  }
  if (retryAfter === null) {
    return WAIT_WITHOUT_RETRY_AFTER_MS;
  }
  const seconds = /^\d+$/.test(retryAfter) ? Number(retryAfter) : Infinity;
  return seconds <= LONGEST_WAIT_S ? seconds * MS_PER_SECOND : null;
}

function primaryUsage(usage: unknown): Usage {
  if (!isObject(usage)) {
    throw new ProviderFailure(MALFORMED);
  }
  return usageOf(usage.prompt_tokens, usage.completion_tokens);
}

/** The pieces of one event: its text, then its usage, either of which may be absent. */
function piecesOf(data: string): Piece[] {
  const chunk = providerJson(data);
  if (!Array.isArray(chunk.choices)) {
    throw new ProviderFailure(MALFORMED);
  }
  const pieces: Piece[] = chunk.choices
    .map((choice: unknown) => (isObject(choice) && isObject(choice.delta) ? choice.delta.content : null))
    .filter((text: unknown): text is string => typeof text === "string" && text !== "")
    .map((text: string) => ({ text }));
  if (chunk.usage !== undefined) {
    pieces.push({ usage: primaryUsage(chunk.usage) });
  }
  return pieces;
}

export class PrimaryProvider implements Provider {
  readonly name = "primary";
  readonly model = "brisk-1";
  readonly #url: string;
  readonly #key: string;

  constructor(url: string, key: string) {
    this.#url = url;
    this.#key = key;
  }

  async complete(ask: Ask): Promise<Answer> {
    const answer = await wholeBody(await this.#opened(ask, false));
    const [choice] = Array.isArray(answer.choices) ? answer.choices : [];
    const content = isObject(choice) && isObject(choice.message) ? choice.message.content : null;
    if (typeof content !== "string") {
      throw new ProviderFailure(MALFORMED);
    }
    return { content, usage: primaryUsage(answer.usage) };
  }

  async *stream(ask: Ask): AsyncGenerator<Piece> {
    const attempt = await this.#opened(ask, true);
    for await (const { data } of serverSentEvents(streamBody(attempt))) {
      if (data === END_OF_STREAM) {
        return;
      }
      yield* piecesOf(data);
    }
    throw new ProviderFailure(ENDED_EARLY);
  }

  /** A 2xx answer, after waiting out up to two 429s; anything else is a failure. */
  async #opened(ask: Ask, stream: boolean): Promise<Attempt> {
    for (let sent = 1; ; sent += 1) {
      const attempt = await send({
        url: `${this.#url}/v1/chat/completions`,
        headers: { Authorization: `Bearer ${this.#key}` },
        body: { model: this.model, messages: ask.messages, max_tokens: ask.maxTokens, stream },
        signal: ask.signal,
      });
      const { status, headers, ok } = attempt.response;
      if (ok) {
        return attempt;
      }
      await discard(attempt);
      const wait = waitBeforeRetry(status, headers.get("retry-after"));
      if (wait === null || sent === MAX_REQUESTS) {
        throw new ProviderFailure(`the primary answered ${status}`);
      }
      await sleep(wait);
    }
  }
}
