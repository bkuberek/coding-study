// The model services as the rest of the app uses them: a 429 is waited out and sent again, and
// anything else that is not a usable answer is a ProviderError naming the service.

import { requestChat, requestEmbeddings } from "./providers.ts";
import type { ChatMessage, ProviderAnswer } from "./providers.ts";

const ATTEMPTS = 3;
const DEFAULT_WAIT_S = 1;
const WHOLE_SECONDS = /^\d+$/;

export class ProviderError extends Error {
  readonly code: "embeddings_unavailable" | "model_unavailable";

  constructor(code: ProviderError["code"], message: string) {
    super(message);
    this.code = code;
  }
}

export type Reply = { answer: string; citations: string[] };

// One vector per text, in the order of `texts`.
export async function embed(texts: string[]): Promise<number[][]> {
  const answer = await sentWithRetries("embeddings_unavailable", () => requestEmbeddings(texts));
  const vectors = vectorsIn(answer.body, texts.length);
  if (answer.status !== 200 || vectors === null) {
    throw unusable("embeddings_unavailable", answer);
  }
  return vectors;
}

// The model's reply to `messages`, read as the JSON object the system prompt asks for.
export async function complete(messages: ChatMessage[]): Promise<Reply> {
  const answer = await sentWithRetries("model_unavailable", () => requestChat(messages));
  const reply = replyIn(answer.body);
  if (answer.status !== 200 || reply === null) {
    throw unusable("model_unavailable", answer);
  }
  return reply;
}

async function sentWithRetries(
  code: ProviderError["code"],
  send: () => Promise<ProviderAnswer>,
): Promise<ProviderAnswer> {
  for (let attempt = 1; ; attempt += 1) {
    let answer: ProviderAnswer;
    try {
      answer = await send();
    } catch (error) {
      throw new ProviderError(code, `no answer: ${String(error)}`);
    }
    if (answer.status !== 429 || attempt === ATTEMPTS) {
      return answer;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000 * secondsToWait(answer.retryAfter)));
  }
}

function secondsToWait(retryAfter: string | null): number {
  return retryAfter !== null && WHOLE_SECONDS.test(retryAfter) ? Number(retryAfter) : DEFAULT_WAIT_S;
}

function unusable(code: ProviderError["code"], answer: ProviderAnswer): ProviderError {
  return new ProviderError(code, `answered ${answer.status}: ${JSON.stringify(answer.body)}`);
}

function vectorsIn(body: unknown, count: number): number[][] | null {
  const data = (body as { data?: unknown } | null)?.data;
  if (!Array.isArray(data) || data.length !== count) {
    return null;
  }
  const items = data as { index?: unknown; embedding?: unknown }[];
  const vectors = items.map((_, position) => items.find((item) => item.index === position)?.embedding);
  return vectors.every(Array.isArray) ? (vectors as number[][]) : null;
}

function replyIn(body: unknown): Reply | null {
  const content = (body as { choices?: { message?: { content?: unknown } }[] } | null)?.choices?.[0]
    ?.message?.content;
  if (typeof content !== "string") {
    return null;
  }
  let reply: unknown;
  try {
    reply = JSON.parse(content);
  } catch {
    return null;
  }
  const { answer, citations } = (reply ?? {}) as { answer?: unknown; citations?: unknown };
  const cited = Array.isArray(citations) && citations.every((id) => typeof id === "string");
  return typeof answer === "string" && cited ? { answer, citations: citations as string[] } : null;
}
