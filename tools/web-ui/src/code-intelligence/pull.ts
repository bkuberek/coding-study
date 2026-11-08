/**
 * Pull diagnostics (docs/specs/web-ui.md#live-diagnostics): a server that declares a
 * `diagnosticProvider` is asked for a file's diagnostics with `textDocument/diagnostic` once the
 * file opens and after each change the page sends, and for every open file again when it asks for
 * a refresh, which the broker passes on as `cstudy/diagnosticRefresh`. A report replaces the
 * file's pulled diagnostics, beside those the server publishes: rust-analyzer answers for its own
 * diagnostics and publishes those of `cargo check`. While it loads its workspace, rust-analyzer
 * answers with an empty report, then cancels pulls (`ServerCancelled`, `retriggerRequest` true)
 * at each step of the load, so a cancelled pull is asked again, waiting longer each time.
 */

import type { LSPClient } from "@codemirror/lsp-client";

import { type PublishedDiagnostic } from "./live-diagnostics.ts";
import { markFile } from "./publish.ts";

export const PULL_AGAIN = "cstudy/diagnosticRefresh";
/** How long the first retry of a cancelled pull waits; each later one waits twice as long. */
export const FIRST_RETRY_MS = 500;
/** The longest wait between two tries of a cancelled pull. */
export const LONGEST_RETRY_MS = 8_000;
/** How many times a cancelled pull is asked again: about 40 seconds of a workspace loading. */
export const MAX_RETRIES = 8;
const SERVER_CANCELLED = -32802;
const CONTENT_MODIFIED = -32801;

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

/**
 * Whether a failed pull is to be asked again: one the server cancelled (`ServerCancelled`) unless
 * it said not to (`retriggerRequest` false), or one cancelled because the content changed.
 */
export function retriggers(error: unknown): boolean {
  if (typeof error !== "object" || error === null || !("code" in error)) return false;
  if (error.code === CONTENT_MODIFIED) return true;
  const data = "data" in error && typeof error.data === "object" && error.data !== null ? error.data : {};
  return error.code === SERVER_CANCELLED && !("retriggerRequest" in data && data.retriggerRequest === false);
}

/** How long the retry after `attempt` earlier ones waits: 500 ms, then twice as long, up to 8 s. */
export function retryDelay(attempt: number): number {
  return Math.min(FIRST_RETRY_MS * 2 ** attempt, LONGEST_RETRY_MS);
}

/**
 * Asks the server for the file's diagnostics once the connection is initialized, if it answers
 * such requests, and marks the file with them unless it changed meanwhile: a pull follows each
 * change. A pull the server cancelled is asked again, up to `MAX_RETRIES` times, while the file is
 * open and unchanged; `attempt` counts the tries so far.
 */
export function pullDiagnostics(client: LSPClient, uri: string, attempt = 0): void {
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
        if (attempt < MAX_RETRIES && retriggers(error)) {
          setTimeout(() => {
            if (client.workspace.getFile(uri)?.version === version) pullDiagnostics(client, uri, attempt + 1);
          }, retryDelay(attempt));
        }
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
