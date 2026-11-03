/**
 * `@codemirror/lsp-client`'s client, with one change: a notification belongs to the connection it
 * was made on. The client queues notifications behind `initializing`, and a session reconnects
 * with the same client, so a `didChange` made while the socket was down would otherwise go out
 * after the next `initialize`, for a document that connection never opened. The workspace opens
 * every file again on each connection (`SessionWorkspace.connected`), so nothing is lost.
 */

import { LSPClient, type Transport } from "@codemirror/lsp-client";

export class ServerClient extends LSPClient {
  #generation = 0;
  #transport: Transport | null = null;

  override connect(transport: Transport): this {
    this.#generation += 1;
    this.#transport = transport;
    return super.connect(transport);
  }

  override disconnect(): void {
    this.#generation += 1;
    super.disconnect();
  }

  override notification<Params>(method: string, params: Params): void {
    const transport = this.#transport;
    if (transport === null) return;
    const generation = this.#generation;
    this.initializing
      .then(() => {
        if (generation === this.#generation) transport.send(JSON.stringify({ jsonrpc: "2.0", method, params }));
      })
      // A connection that never initialized is the session's to report.
      .catch(() => {});
  }
}
