/**
 * `textDocument/publishDiagnostics` (docs/specs/web-ui.md#live-diagnostics): each publication
 * replaces the language server's diagnostics for the file, beside the last run's. The client's own
 * `serverDiagnostics()` is not used, since it replaces the editor's whole lint set.
 */

import { type LSPClient, LSPPlugin } from "@codemirror/lsp-client";

import { liveDiagnosticsSpec } from "../diagnostics.ts";
import { liveDiagnostics, lspOffset, type PublishedDiagnostic } from "./live-diagnostics.ts";

interface Publication {
  readonly uri: string;
  readonly version?: number;
  readonly diagnostics: readonly PublishedDiagnostic[];
}

/**
 * Marks the file's tab with the published diagnostics. A publication for a file with no tab is
 * dropped, and so is one for a version the client has since replaced: the server publishes again
 * for the newer one. Positions are those of the text last sent, mapped through what was typed
 * since. Always true: the client handles nothing else with this method.
 */
export function publishDiagnostics(client: LSPClient, params: Publication): boolean {
  const file = client.workspace.getFile(params.uri);
  const view = file?.getView() ?? null;
  const plugin = view === null ? null : LSPPlugin.get(view);
  if (file === null || view === null || plugin === null) return true;
  if (params.version !== undefined && params.version !== null && params.version !== file.version) return true;
  const markers = liveDiagnostics(params.diagnostics, (position) =>
    plugin.unsyncedChanges.mapPos(lspOffset(plugin.syncedDoc, position)),
  );
  view.dispatch(liveDiagnosticsSpec(view.state, markers));
  return true;
}
