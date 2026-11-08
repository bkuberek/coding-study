/**
 * Pull diagnostics (docs/specs/web-ui.md#live-diagnostics): a server that declares a
 * `diagnosticProvider` is asked for a file's diagnostics with `textDocument/diagnostic` once the
 * file opens and after each change the page sends, and for every open file again when it asks for
 * a refresh, which the broker passes on as `cstudy/diagnosticRefresh`. A report replaces the
 * file's pulled diagnostics, beside those the server publishes: rust-analyzer answers for its own
 * diagnostics and publishes those of `cargo check`.
 */

import type { LSPClient } from "@codemirror/lsp-client";

import { type PublishedDiagnostic } from "./live-diagnostics.ts";
import { markFile } from "./publish.ts";

export const PULL_AGAIN = "cstudy/diagnosticRefresh";
/** How long a pull the server cancelled, asking to be asked again, waits before it is. */
export const RETRY_MS = 500;

interface ServerCapabilities {
  readonly diagnosticProvider?: unknown;
}

/** Whether the server answers `textDocument/diagnostic`. */
export function pullsDiagnostics(capabilities: ServerCapabilities | null): boolean {
  return Boolean(capabilities?.diagnosticProvider);
}

/** The parameters of a pull for the file, with the provider's identifier when it declares one. */
export function pullParams(uri: string, provider: unknown): { textDocument: { uri: string }; identifier?: string } {
  const identifier = typeof provider === "object" && provider !== null && "identifier" in provider ? provider.identifier : undefined;
  return typeof identifier === "string" ? { textDocument: { uri }, identifier } : { textDocument: { uri } };
}

/** The diagnostics of a full report; null for any other answer, which changes nothing. */
export function pulledItems(report: unknown): readonly PublishedDiagnostic[] | null {
  if (typeof report !== "object" || report === null) return null;
  const { kind, items } = report as { kind?: unknown; items?: unknown };
  return kind === "full" && Array.isArray(items) ? (items as PublishedDiagnostic[]) : null;
}

/** Whether a failed pull is one the server cancelled, asking to be asked again. */
export function retriggers(error: unknown): boolean {
  const data = typeof error === "object" && error !== null && "data" in error ? error.data : undefined;
  return typeof data === "object" && data !== null && "retriggerRequest" in data && data.retriggerRequest === true;
}

/**
 * Asks the server for the file's diagnostics once the connection is initialized, if it answers
 * such requests, and marks the file with them unless it changed meanwhile: a pull follows each
 * change. A pull the server cancelled, asking to be asked again, is asked once more.
 */
export function pullDiagnostics(client: LSPClient, uri: string, retry = true): void {
  client.initializing
    .then(async () => {
      const provider = client.serverCapabilities?.diagnosticProvider;
      const file = client.workspace.getFile(uri);
      if (!provider || file === null) return;
      const version = file.version;
      try {
        const report = await client.request<unknown, unknown>("textDocument/diagnostic", pullParams(uri, provider));
        const items = pulledItems(report);
        if (items !== null) markFile(client, { uri, version, diagnostics: items }, "pulled");
      } catch (error) {
        if (retry && retriggers(error)) setTimeout(() => pullDiagnostics(client, uri, false), RETRY_MS);
      }
    })
    // A connection that never initialized is the session's to report.
    .catch(() => {});
}

/** Asks again for every open file, as a server's refresh asks. Always true: nothing else handles it. */
export function pullAgain(client: LSPClient): boolean {
  for (const file of client.workspace.files) pullDiagnostics(client, file.uri);
  return true;
}
