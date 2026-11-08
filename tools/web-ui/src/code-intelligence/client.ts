/**
 * `@codemirror/lsp-client`'s client, with one change: a notification belongs to the connection it
 * was made on. The client queues notifications behind `initializing`, and a session reconnects
 * with the same client, so a `didChange` made while the socket was down would otherwise go out
 * after the next `initialize`, for a document that connection never opened. The workspace opens
 * every file again on each connection (`SessionWorkspace.connected`), so nothing is lost. And a
 * second: after it sends a file's changes, it pulls the file's diagnostics from a server that
 * answers for them.
 */

import { LSPClient, LSPPlugin, type Transport, type WorkspaceFile } from "@codemirror/lsp-client";

import { pullDiagnostics } from "./pull.ts";

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

  /** Sends the changes of the open files, then asks for the diagnostics of each file that changed. */
  override sync(): void {
    const changed = this.workspace.files.filter(hasUnsyncedChanges).map((file) => file.uri);
    super.sync();
    for (const uri of changed) pullDiagnostics(this, uri);
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

function hasUnsyncedChanges(file: WorkspaceFile): boolean {
  const view = file.getView();
  const plugin = view === null ? null : LSPPlugin.get(view);
  return plugin !== null && !plugin.unsyncedChanges.empty;
}
