// What a team asks for, checked before any provider hears of it.

import { isObject } from "./provider.ts";

export const DEFAULT_MAX_TOKENS = 256;

export type ChatRequest = { team: string; messages: unknown[]; maxTokens: number; stream: boolean };

/** A request the gateway refuses: its message is the caller's error. */
export class Refusal extends Error {}

function jsonObject(text: string): Record<string, unknown> {
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    throw new Refusal("the body must be a JSON object");
  }
  if (!isObject(value)) {
    throw new Refusal("the body must be a JSON object");
  }
  return value;
}

export function chatRequest(team: string | undefined, text: string): ChatRequest {
  if (team === undefined) {
    throw new Refusal("X-Team is required");
  }
  const { messages, max_tokens: maxTokens, stream } = jsonObject(text);
  if (!Array.isArray(messages) || messages.length === 0) {
    throw new Refusal("messages must be a non-empty list");
  }
  if (maxTokens !== undefined && !(Number.isInteger(maxTokens) && (maxTokens as number) > 0)) {
    throw new Refusal("max_tokens must be a positive integer");
  }
  return {
    team,
    messages,
    maxTokens: (maxTokens as number | undefined) ?? DEFAULT_MAX_TOKENS,
    stream: stream === true,
  };
}

/** The tokens of a budget. */
export function budgetTokens(text: string): number {
  const { tokens } = jsonObject(text);
  if (!Number.isInteger(tokens) || (tokens as number) < 0) {
    throw new Refusal("tokens must be a non-negative integer");
  }
  return tokens as number;
}
