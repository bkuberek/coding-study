// Replays the answer to a write that already succeeded. It sits in front of every write, so that a
// handler never has to think about retries, and it runs first, because the state a retry finds says
// nothing about the first attempt: the version has moved on, or the record is gone.

import { ApiError } from "./errors.ts";
import { canonicalJson } from "./json.ts";
import type { Answer, Route, RouteRequest } from "./router.ts";

interface Replay {
  fingerprint: string;
  status: number;
  /** The answer as text, frozen the moment it was first given. */
  body: string;
}

export class ReplayStore {
  readonly #replays = new Map<string, Replay>();

  find(requestId: string): Replay | undefined {
    return this.#replays.get(requestId);
  }

  save(requestId: string, replay: Replay): void {
    this.#replays.set(requestId, replay);
  }
}

/** The body as an object if it is one; bad bodies are for the handler to refuse. */
function parsedBody(text: string): Record<string, unknown> | null {
  try {
    const parsed: unknown = JSON.parse(text);
    return parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

function isSuccess(status: number): boolean {
  return status >= 200 && status < 300;
}

export function withReplay(store: ReplayStore, handle: Route["handle"]): Route["handle"] {
  return (request: RouteRequest): Answer => {
    const body = parsedBody(request.body);
    const requestId = body?.requestId;
    if (typeof requestId !== "string" || requestId === "") {
      return handle(request);
    }
    const fingerprint = `${request.method} ${request.path} ${canonicalJson(body)}`;
    const replay = store.find(requestId);
    if (replay !== undefined) {
      if (replay.fingerprint !== fingerprint) {
        throw new ApiError(422, "request_id_reused", `requestId ${requestId} was used for a different request`);
      }
      return { status: replay.status, body: JSON.parse(replay.body) };
    }
    const answer = handle(request);
    if (isSuccess(answer.status)) {
      store.save(requestId, { fingerprint, status: answer.status, body: canonicalJson(answer.body) });
    }
    return answer;
  };
}
