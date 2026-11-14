// The gateway: asks each provider in turn until one answers, and commits to it at the first piece of
// text that reaches the caller.

import type { ServerResponse } from "node:http";

import { answer } from "./http.ts";
import type { TeamLedger } from "./ledger.ts";
import { ProviderFailure } from "./provider.ts";
import type { Ask, Piece, Provider } from "./provider.ts";

const NO_PROVIDER = { error: "no provider answered" };
const END_OF_STREAM = "data: [DONE]\n\n";

function dataEvent(document: unknown): string {
  return `data: ${JSON.stringify(document)}\n\n`;
}

function errorEvent(message: string): string {
  return `event: error\ndata: ${JSON.stringify({ error: message })}\n\n`;
}

function failureOf(error: unknown): ProviderFailure {
  if (error instanceof ProviderFailure) {
    return error;
  }
  throw error;
}

/** The first piece of a stream; null when the stream gave none, so nothing has reached the caller
 * and the next provider may still answer. */
async function firstPiece(pieces: AsyncGenerator<Piece>): Promise<Piece | null> {
  try {
    const first = await pieces.next();
    return first.done ? null : first.value;
  } catch (error) {
    failureOf(error);
    return null;
  }
}

export class Gateway {
  readonly #providers: readonly Provider[];
  readonly #ledger: TeamLedger;

  constructor(providers: readonly Provider[], ledger: TeamLedger) {
    this.#providers = providers;
    this.#ledger = ledger;
  }

  async whole(team: string, ask: Ask, response: ServerResponse): Promise<void> {
    for (const provider of this.#providers) {
      try {
        const { content, usage } = await provider.complete(ask);
        this.#ledger.record(team, provider.model, usage);
        answer(response, 200, { provider: provider.name, content, usage });
        return;
      } catch (error) {
        failureOf(error);
      }
    }
    answer(response, 502, NO_PROVIDER);
  }

  async stream(team: string, ask: Ask, response: ServerResponse): Promise<void> {
    for (const provider of this.#providers) {
      const pieces = provider.stream(ask);
      const first = await firstPiece(pieces);
      if (first !== null) {
        response.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" });
        await this.#relay(team, provider, first, pieces, response);
        return;
      }
    }
    answer(response, 502, NO_PROVIDER);
  }

  /** Writes each piece as it arrives. Past the first, the answer is this provider's: a break ends
   * it with an error event, never with another provider's answer or a `[DONE]`. */
  async #relay(
    team: string,
    provider: Provider,
    first: Piece,
    rest: AsyncGenerator<Piece>,
    response: ServerResponse,
  ): Promise<void> {
    try {
      let next: IteratorResult<Piece> = { done: false, value: first };
      while (!next.done) {
        const piece = next.value;
        if ("usage" in piece) {
          this.#ledger.record(team, provider.model, piece.usage);
        }
        response.write(eventOf(provider, piece));
        next = await rest.next();
      }
      response.write(END_OF_STREAM);
    } catch (error) {
      response.write(errorEvent(failureOf(error).message));
    }
    response.end();
  }
}

function eventOf(provider: Provider, piece: Piece): string {
  if ("text" in piece) {
    return dataEvent({ delta: piece.text });
  }
  return dataEvent({ provider: provider.name, usage: piece.usage });
}
