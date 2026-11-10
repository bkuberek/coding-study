// The checks on what a request sends. Each returns what the route needs, or null for a request to
// refuse with 400.

import { wordsOf } from "./chunking.ts";

const DOCUMENT_ID = /^[a-z0-9-]{1,40}$/;
const MAX_K = 10;

export type SearchRequest = { query: string; k: number; minScore: number };

export function isDocumentId(id: string): boolean {
  return DOCUMENT_ID.test(id);
}

// The words of the document's text, at least one.
export function documentWords(body: unknown): string[] | null {
  const text = fieldOf(body, "text");
  const words = typeof text === "string" ? wordsOf(text) : [];
  return words.length === 0 ? null : words;
}

export function searchRequest(
  body: unknown,
  defaults: { k: number; minScore: number },
): SearchRequest | null {
  const query = textField(body, "query");
  const k = fieldOf(body, "k") ?? defaults.k;
  const minScore = fieldOf(body, "min_score") ?? defaults.minScore;
  const kValid = Number.isInteger(k) && (k as number) >= 1 && (k as number) <= MAX_K;
  const minValid = typeof minScore === "number" && minScore >= 0 && minScore <= 1;
  if (query === null || !kValid || !minValid) {
    return null;
  }
  return { query, k: k as number, minScore };
}

export function question(body: unknown): string | null {
  return textField(body, "question");
}

// A field that is a string holding something other than whitespace.
function textField(body: unknown, name: string): string | null {
  const value = fieldOf(body, name);
  return typeof value === "string" && value.trim() !== "" ? value : null;
}

function fieldOf(body: unknown, name: string): unknown {
  const isObject = typeof body === "object" && body !== null && !Array.isArray(body);
  return isObject ? (body as Record<string, unknown>)[name] : undefined;
}
