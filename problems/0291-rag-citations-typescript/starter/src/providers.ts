// The clients of the team's two model services: the embeddings service at `EMBEDDINGS_URL` and the
// chat model at `CHAT_URL`, both behind the key in `LLM_API_KEY`. Their contracts are in
// vendors/embeddings/API.md and vendors/chat/API.md. Each function sends its request once: what to
// do with a 429 or a failure is yours to decide.

export const EMBEDDING_MODEL = "help-embed-1";
export const CHAT_MODEL = "help-chat-1";

// The system message the chat model is given, word for word.
export const SYSTEM_PROMPT =
  "Answer the question using only the sources. Each source starts with its id in brackets. Reply " +
  "with a JSON object: answer, a short text, and citations, the list of source ids the answer uses. " +
  "When the sources do not answer the question, reply with the answer I don't know. and no citations.";

const TIMEOUT_MS = 5000;

// `body` is the parsed JSON, or the text as it came when it is not JSON. `retryAfter` is the
// `Retry-After` header, or null.
export type ProviderAnswer = { status: number; body: unknown; retryAfter: string | null };

export type ChatPart = { type: "text"; text: string };
export type ChatMessage =
  | { role: "system"; content: string }
  | { role: "user"; content: ChatPart[] };

// Throws when the service cannot be reached or takes longer than TIMEOUT_MS.
export async function requestEmbeddings(texts: string[]): Promise<ProviderAnswer> {
  return post(`${process.env.EMBEDDINGS_URL}/v1/embeddings`, {
    model: EMBEDDING_MODEL,
    input: texts,
  });
}

// Throws when the service cannot be reached or takes longer than TIMEOUT_MS.
export async function requestChat(messages: ChatMessage[]): Promise<ProviderAnswer> {
  return post(`${process.env.CHAT_URL}/v1/chat/completions`, { model: CHAT_MODEL, messages });
}

async function post(url: string, payload: unknown): Promise<ProviderAnswer> {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.LLM_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  const text = await response.text();
  return {
    status: response.status,
    body: parsedOrText(text),
    retryAfter: response.headers.get("retry-after"),
  };
}

function parsedOrText(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}
