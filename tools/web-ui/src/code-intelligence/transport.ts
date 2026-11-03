/**
 * The WebSocket under a session (docs/specs/web-ui.md#sessions): `@codemirror/lsp-client`'s
 * `Transport` over one socket, one JSON-RPC message per text frame.
 */

import type { Transport } from "@codemirror/lsp-client";

const SESSION_PATH = "/api/v1/code-intelligence";
const OPEN = 1;

export interface Origin {
  readonly protocol: string;
  readonly host: string;
}

/** The session's URL on the page's own host and port; `connect-src 'self'` covers it. */
export function sessionUrl(origin: Origin, attemptId: number): string {
  const scheme = origin.protocol === "https:" ? "wss:" : "ws:";
  return `${scheme}//${origin.host}${SESSION_PATH}?attempt_id=${attemptId}`;
}

/**
 * A message sent while the socket is not open is dropped, not thrown: the client sends from
 * promise callbacks nobody awaits, and a socket that closed in between is the session's to
 * handle (it reconnects and opens its files again, so nothing is replayed).
 */
export class SocketTransport implements Transport {
  readonly #socket: WebSocket;
  readonly #handlers = new Set<(value: string) => void>();

  constructor(socket: WebSocket) {
    this.#socket = socket;
  }

  send(message: string): void {
    if (this.#socket.readyState === OPEN) this.#socket.send(message);
  }

  subscribe(handler: (value: string) => void): void {
    this.#handlers.add(handler);
  }

  unsubscribe(handler: (value: string) => void): void {
    this.#handlers.delete(handler);
  }

  /** Passes a text frame from the server to the client. */
  deliver(text: string): void {
    for (const handler of this.#handlers) handler(text);
  }
}
