// What the routes do: put a document, list its chunks, search, and answer with citations.

import { chunkCount, chunksOf, MAX_CHUNKS } from "./chunking.ts";
import { complete, embed } from "./models.ts";
import { SYSTEM_PROMPT } from "./providers.ts";
import type { ChatMessage } from "./providers.ts";
import { chunksOfDocument, nearest, replaceChunks } from "./store.ts";
import type { Hit } from "./store.ts";

export const DEFAULT_K = 3;
export const DEFAULT_MIN_SCORE = 0.6;
export const DONT_KNOW = "I don't know.";

const SCORE_DECIMALS = 10_000;

export type Listing = { chunk_id: string; position: number; text: string }[];
export type Result = {
  chunk_id: string;
  document_id: string;
  position: number;
  score: number;
  text: string;
};
export type Citation = { chunk_id: string; document_id: string; position: number };
export type Answered = { answer: string; citations: Citation[] };

// The number of chunks kept, or null for a document too long to keep. Nothing changes unless every
// chunk was embedded.
export async function putDocument(documentId: string, words: string[]): Promise<number | null> {
  if (chunkCount(words) > MAX_CHUNKS) {
    return null;
  }
  const texts = chunksOf(words);
  await replaceChunks(documentId, texts, await embed(texts));
  return texts.length;
}

// The document's chunks in position order, or null for a document never put.
export async function listChunks(documentId: string): Promise<Listing | null> {
  const chunks = await chunksOfDocument(documentId);
  if (chunks.length === 0) {
    return null;
  }
  return chunks.map((chunk) => ({
    chunk_id: chunkId(documentId, chunk.position),
    position: chunk.position,
    text: chunk.text,
  }));
}

export async function search(query: string, k: number, minScore: number): Promise<Result[]> {
  const hits = await retrieve(query, k, minScore);
  return hits.map((hit) => ({
    ...citationOf(hit),
    score: Math.round(hit.score * SCORE_DECIMALS) / SCORE_DECIMALS,
    text: hit.text,
  }));
}

// Retrieves first, and asks the model only when something passed the minimum, showing it those
// chunks alone. Of the citations it gives back, only chunks it was shown are kept, each once.
export async function ask(question: string): Promise<Answered> {
  const hits = await retrieve(question, DEFAULT_K, DEFAULT_MIN_SCORE);
  if (hits.length === 0) {
    return { answer: DONT_KNOW, citations: [] };
  }
  const reply = await complete(prompt(question, hits));
  return { answer: reply.answer, citations: grounded(reply.citations, hits) };
}

async function retrieve(text: string, k: number, minScore: number): Promise<Hit[]> {
  const [vector] = await embed([text]);
  return nearest(vector, k, minScore);
}

function prompt(question: string, hits: Hit[]): ChatMessage[] {
  const sources = hits.map((hit) => ({
    type: "text" as const,
    text: `[${chunkId(hit.documentId, hit.position)}] ${hit.text}`,
  }));
  return [
    { role: "system", content: SYSTEM_PROMPT },
    { role: "user", content: [...sources, { type: "text", text: `Question: ${question}` }] },
  ];
}

function grounded(cited: string[], hits: Hit[]): Citation[] {
  const shown = new Map(hits.map((hit) => [chunkId(hit.documentId, hit.position), hit]));
  const kept = new Map<string, Citation>();
  for (const id of cited) {
    const hit = shown.get(id);
    if (hit !== undefined && !kept.has(id)) {
      kept.set(id, citationOf(hit));
    }
  }
  return [...kept.values()];
}

function citationOf(hit: Hit): Citation {
  return {
    chunk_id: chunkId(hit.documentId, hit.position),
    document_id: hit.documentId,
    position: hit.position,
  };
}

function chunkId(documentId: string, position: number): string {
  return `${documentId}:${position}`;
}
