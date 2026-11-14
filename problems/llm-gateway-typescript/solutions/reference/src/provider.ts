// The seam between the gateway and its providers: whatever a provider speaks, it answers in these.

export type Usage = { prompt_tokens: number; completion_tokens: number };

/** A piece of a streamed answer, in the order the provider sent it. */
export type Piece = { text: string } | { usage: Usage };

export type Answer = { content: string; usage: Usage };

/** What the gateway asks of a provider: the caller's messages as they came, the most tokens the
 * answer may use, and a signal that fires when the caller has gone. */
export type Ask = { messages: unknown[]; maxTokens: number; signal: AbortSignal };

export interface Provider {
  readonly name: string;
  readonly model: string;
  /** Rejects with a ProviderFailure when the provider gives no usable answer. */
  complete(ask: Ask): Promise<Answer>;
  /** The pieces of a stream as they arrive. Throws a ProviderFailure when the stream cannot start
   * or breaks, and returns at the provider's own end of stream. */
  stream(ask: Ask): AsyncGenerator<Piece>;
}

/** A provider gave no usable answer. Once a stream has started, the message is what the caller's
 * error event says. */
export class ProviderFailure extends Error {}

export const NOT_ANSWERED = "the provider did not answer";
export const ENDED_EARLY = "the provider's stream ended early";
export const STALLED = "the provider's stream stalled";
export const MALFORMED = "the provider sent a malformed event";
export const REPORTED = "the provider reported an error";

export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** A provider's JSON, which must be an object. */
export function providerJson(text: string): Record<string, unknown> {
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    throw new ProviderFailure(MALFORMED);
  }
  if (!isObject(value)) {
    throw new ProviderFailure(MALFORMED);
  }
  return value;
}

/** Usage in the gateway's names and order, from a provider's two counts. */
export function usageOf(prompt: unknown, completion: unknown): Usage {
  if (!Number.isInteger(prompt) || !Number.isInteger(completion)) {
    throw new ProviderFailure(MALFORMED);
  }
  return { prompt_tokens: prompt as number, completion_tokens: completion as number };
}
