/**
 * The decisions of go to definition (docs/specs/web-ui.md#go-to-definition), apart from the
 * editor: where a definition answer points, what kind of file the target is, the note a refused
 * library file gets, which click means a jump, and the stack Back pops.
 */

import type { Position } from "./live-diagnostics.ts";

/** Where the first location of a definition answer points: a URI and a 0-based line and UTF-16 character. */
export interface DefinitionTarget {
  readonly uri: string;
  readonly line: number;
  readonly character: number;
}

export type Target =
  /** The file the cursor is in. */
  | { readonly kind: "same" }
  /** Another file of the attempt's tree: its tab opens or comes forward. */
  | { readonly kind: "attempt"; readonly path: string }
  /** Anything else: the broker is asked to read it, and answers or refuses. */
  | { readonly kind: "library" };

/** A tab a jump started in, or that Back returns to. */
export type TabRef =
  | { readonly kind: "attempt"; readonly path: string }
  | { readonly kind: "library"; readonly uri: string };

/** Where a jump started: the tab and the cursor in it. */
export interface Origin {
  readonly tab: TabRef;
  readonly head: number;
}

const MAX_ORIGINS = 50;

interface Range {
  readonly start: Position;
}

/**
 * The first location of a `textDocument/definition` answer, whichever of its shapes: a
 * `Location`, a list of them, or `LocationLink`s, which `@codemirror/lsp-client`'s own
 * `jumpToDefinition` does not read (it takes `uri` and `range` of the first, which a link lacks).
 * Null for no location.
 */
export function definitionTarget(answer: unknown): DefinitionTarget | null {
  const found: unknown = Array.isArray(answer) ? answer[0] : answer;
  if (typeof found !== "object" || found === null) return null;
  const link = found as { targetUri?: unknown; targetSelectionRange?: Range; targetRange?: Range };
  const place = found as { uri?: unknown; range?: Range };
  const uri = link.targetUri ?? place.uri;
  const start = (link.targetSelectionRange ?? link.targetRange ?? place.range)?.start;
  if (typeof uri !== "string" || start === undefined) return null;
  return { uri, line: start.line, character: start.character };
}

/**
 * What the target is, given the file the cursor is in, the session's root and the paths of the
 * attempt's tree: a file inside the root that the tree lists is the attempt's, every other URI is
 * a library file for the broker to read or refuse.
 */
export function classifyTarget(uri: string, ownUri: string, rootUri: string, tree: ReadonlySet<string>): Target {
  if (uri === ownUri) return { kind: "same" };
  const prefix = `${rootUri}/`;
  if (!uri.startsWith(prefix)) return { kind: "library" };
  const path = uri
    .slice(prefix.length)
    .split("/")
    .map((segment) => decodeURIComponent(segment))
    .join("/");
  return tree.has(path) ? { kind: "attempt", path } : { kind: "library" };
}

const REASONS: Readonly<Record<string, string>> = {
  too_large: "over 4 MiB",
  not_text: "not UTF-8 text",
  missing: "no such file",
  not_a_file: "not a regular file",
  not_a_file_uri: "not a file: URI",
};
const BUILD_AREA = "build_area";
const BUILD_AREA_NOTE = "not shown: cstudy's build area";

/**
 * The note at the click for a library file the broker refused: the file, the 1-based line and the
 * reason (`python/.venv/lib/big.py:120 · over 4 MiB`); the build area's refusal is only its own
 * words. Anything else that went wrong is its message.
 */
export function refusalNote(error: unknown, line: number): string {
  const { message, data } = error as { message?: unknown; data?: { reason?: unknown; path?: unknown } };
  const reason = data?.reason;
  if (reason === BUILD_AREA) return BUILD_AREA_NOTE;
  if (typeof reason === "string" && reason in REASONS && typeof data?.path === "string") {
    return `${data.path}:${line + 1} · ${REASONS[reason]}`;
  }
  return typeof message === "string" ? message : String(error);
}

export interface Modifiers {
  readonly metaKey: boolean;
  readonly ctrlKey: boolean;
  readonly altKey: boolean;
  readonly shiftKey: boolean;
}

/** Cmd on macOS, Ctrl elsewhere (on macOS Ctrl-click is the context menu); with Alt or Shift it is not a jump. */
export function isDefinitionClick(event: Modifiers, mac: boolean): boolean {
  if (event.altKey || event.shiftKey) return false;
  return mac ? event.metaKey && !event.ctrlKey : event.ctrlKey && !event.metaKey;
}

/** The last 50 places a jump started in; Back takes the newest. */
export class JumpStack {
  #origins: Origin[] = [];

  get size(): number {
    return this.#origins.length;
  }

  push(origin: Origin): void {
    this.#origins.push(origin);
    if (this.#origins.length > MAX_ORIGINS) this.#origins.shift();
  }

  /** Takes the newest origin that `showable` accepts; those it refuses are dropped. */
  pop(showable: (origin: Origin) => boolean): Origin | null {
    for (let origin = this.#origins.pop(); origin !== undefined; origin = this.#origins.pop()) {
      if (showable(origin)) return origin;
    }
    return null;
  }
}
