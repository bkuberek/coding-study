// The secondary provider: its own path, key header, limit name and named events, asked only once.

import { ENDED_EARLY, MALFORMED, ProviderFailure, REPORTED, isObject, providerJson, usageOf } from "./provider.ts";
import type { Answer, Ask, Piece, Provider, Usage } from "./provider.ts";
import { serverSentEvents } from "./sse.ts";
import type { ServerSentEvent } from "./sse.ts";
import { discard, send, streamBody, wholeBody } from "./upstream.ts";
import type { Attempt } from "./upstream.ts";

function secondaryUsage(usage: unknown): Usage {
  if (!isObject(usage)) {
    throw new ProviderFailure(MALFORMED);
  }
  return usageOf(usage.input_tokens, usage.output_tokens);
}

/** The piece an event carries; null for an event that carries none. */
function pieceOf({ event, data }: ServerSentEvent): Piece | null {
  if (event === "error") {
    throw new ProviderFailure(REPORTED);
  }
  if (event === "delta") {
    const { text } = providerJson(data);
    if (typeof text !== "string") {
      throw new ProviderFailure(MALFORMED);
    }
    return { text };
  }
  return event === "usage" ? { usage: secondaryUsage(providerJson(data)) } : null;
}

export class SecondaryProvider implements Provider {
  readonly name = "secondary";
  readonly model = "steady-2";
  readonly #url: string;
  readonly #key: string;

  constructor(url: string, key: string) {
    this.#url = url;
    this.#key = key;
  }

  async complete(ask: Ask): Promise<Answer> {
    const answer = await wholeBody(await this.#opened(ask, false));
    const content = isObject(answer.output) ? answer.output.text : null;
    if (typeof content !== "string") {
      throw new ProviderFailure(MALFORMED);
    }
    return { content, usage: secondaryUsage(answer.usage) };
  }

  async *stream(ask: Ask): AsyncGenerator<Piece> {
    const attempt = await this.#opened(ask, true);
    for await (const event of serverSentEvents(streamBody(attempt))) {
      if (event.event === "end") {
        return;
      }
      const piece = pieceOf(event);
      if (piece !== null) {
        yield piece;
      }
    }
    throw new ProviderFailure(ENDED_EARLY);
  }

  async #opened(ask: Ask, stream: boolean): Promise<Attempt> {
    const attempt = await send({
      url: `${this.#url}/v1/messages`,
      headers: { "X-Api-Key": this.#key },
      body: { model: this.model, messages: ask.messages, max_output_tokens: ask.maxTokens, stream },
      signal: ask.signal,
    });
    if (!attempt.response.ok) {
      await discard(attempt);
      throw new ProviderFailure(`the secondary answered ${attempt.response.status}`);
    }
    return attempt;
  }
}
