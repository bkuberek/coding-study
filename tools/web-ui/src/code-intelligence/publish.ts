/**
 * `textDocument/publishDiagnostics` (docs/specs/web-ui.md#live-diagnostics): each publication
 * replaces the language server's published diagnostics for the file, beside those the page pulled
 * and the last run's. The client's own `serverDiagnostics()` is not used, since it replaces the
 * editor's whole lint set.
 */

import { type LSPClient, LSPPlugin } from "@codemirror/lsp-client";

import { type LiveSource, liveDiagnosticsSpec } from "../diagnostics.ts";
import { liveDiagnostics, lspOffset, type PublishedDiagnostic } from "./live-diagnostics.ts";

interface Publication {
  readonly uri: string;
  readonly version?: number | null;
  readonly diagnostics: readonly PublishedDiagnostic[];
}

/** Marks the file's tab with the published diagnostics. Always true: the client handles nothing else with this method. */
export function publishDiagnostics(client: LSPClient, params: Publication): boolean {
  markFile(client, params, "pushed");
  return true;
}

/**
 * Makes `diagnostics` the file's diagnostics of `source`. Diagnostics for a file with no tab are
 * dropped, and so are those for a version the client has since replaced: the server answers
 * again for the newer one. Positions are those of the text last sent, mapped through what was
 * typed since.
 */
export function markFile(client: LSPClient, { uri, version, diagnostics }: Publication, source: LiveSource): void {
  const file = client.workspace.getFile(uri);
  const view = file?.getView() ?? null;
  const plugin = view === null ? null : LSPPlugin.get(view);
  if (file === null || view === null || plugin === null) return;
  if (version !== undefined && version !== null && version !== file.version) return;
  const markers = liveDiagnostics(diagnostics, (position) => plugin.unsyncedChanges.mapPos(lspOffset(plugin.syncedDoc, position)));
  view.dispatch(liveDiagnosticsSpec(view.state, markers, source));
}
