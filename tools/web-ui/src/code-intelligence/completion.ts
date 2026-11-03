/**
 * Completion from a language server (docs/specs/web-ui.md#autocomplete), apart from the editor:
 * items to `@codemirror/autocomplete` options, what is asked and when, whether a list stays
 * valid as the word is typed, an item resolved once, and which completion an editor has.
 * `@codemirror/lsp-client`'s `serverCompletion` is not used: it never sends
 * `completionItem/resolve`, so the servers' items would show no signature or documentation.
 */

import type { Completion, CompletionResult } from "@codemirror/autocomplete";

import type { Position } from "./live-diagnostics.ts";

/** What an item's info panel shows: a node, or nothing. */
export type Info = (item: CompletionItem) => Node | null | Promise<Node | null>;

interface Range {
  readonly start: Position;
  readonly end: Position;
}

/** The part of an LSP `CompletionItem` the page reads. */
export interface CompletionItem {
  readonly label: string;
  readonly kind?: number | undefined;
  readonly detail?: string | undefined;
  readonly labelDetails?: { readonly detail?: string; readonly description?: string } | undefined;
  readonly sortText?: string | undefined;
  readonly insertText?: string | undefined;
  /** 2 is a snippet. */
  readonly insertTextFormat?: number | undefined;
  readonly textEdit?: { readonly newText: string; readonly range?: Range; readonly insert?: Range; readonly replace?: Range } | undefined;
  readonly documentation?: unknown;
  readonly [other: string]: unknown;
}

export interface CompletionList {
  readonly items: readonly CompletionItem[];
  readonly isIncomplete?: boolean | undefined;
}

/** A list stays valid while the word is typed on; an incomplete one is asked for again. */
export const VALID_FOR_COMPLETE = /^[\w$]*$/;

const SNIPPET = 2;
const MAX_BOOST = 99;
const TYPES: Readonly<Record<number, Completion["type"]>> = {
  1: "text",
  2: "method",
  3: "function",
  4: "function",
  5: "property",
  6: "variable",
  7: "class",
  8: "interface",
  9: "namespace",
  10: "property",
  11: "constant",
  12: "constant",
  13: "enum",
  14: "keyword",
  15: "text",
  16: "constant",
  17: "text",
  18: "text",
  19: "text",
  20: "enum",
  21: "constant",
  22: "class",
  23: "function",
  24: "keyword",
  25: "type",
};

/** CodeMirror's icon for an LSP completion item kind, if it has one. */
export function kindType(kind: number | undefined): Completion["type"] {
  return kind === undefined ? undefined : TYPES[kind];
}

/**
 * What accepting an item inserts, as plain text: the `newText` of its edit, else its `insertText`,
 * else its label. An item marked as a snippet inserts its label, since the page declares no
 * snippet support and could not step through placeholders.
 */
export function insertedText(item: CompletionItem): string {
  if (item.insertTextFormat === SNIPPET) return item.label;
  return item.textEdit?.newText ?? item.insertText ?? item.label;
}

/** The options of a list, in the order the server sent them; its `sortText` order sets their boost. */
export function completionOptions(items: readonly CompletionItem[], info?: Info): Completion[] {
  const ranked = [...items].sort((a, b) => (a.sortText ?? a.label).localeCompare(b.sortText ?? b.label));
  const rank = new Map(ranked.map((item, index) => [item, index]));
  return items.map((item) => {
    const detail = item.labelDetails?.detail ?? item.detail;
    const type = kindType(item.kind);
    const option: Completion = {
      label: item.label,
      apply: insertedText(item),
      boost: Math.max(-MAX_BOOST, MAX_BOOST - (rank.get(item) ?? 0)),
    };
    if (detail !== undefined) option.detail = detail;
    if (type !== undefined) option.type = type;
    if (info !== undefined) option.info = () => info(item);
    return option;
  });
}

export interface RequestInput {
  /** Ctrl-Space, or another explicit ask. */
  readonly explicit: boolean;
  /** The word characters before the cursor. */
  readonly word: string;
  /** The character before the cursor. */
  readonly before: string;
  /** The server's trigger characters. */
  readonly triggers: readonly string[];
}

/** LSP's `CompletionContext`, or null when nothing was typed that asks for completion. */
export function completionRequest(input: RequestInput): { triggerKind: number; triggerCharacter?: string } | null {
  if (input.triggers.includes(input.before)) return { triggerKind: 2, triggerCharacter: input.before };
  return input.word !== "" || input.explicit ? { triggerKind: 1 } : null;
}

/** A server's answer as CodeMirror's result for the word starting at `from`; null for no items. */
export function completionResult(answer: CompletionList | readonly CompletionItem[] | null, from: number, info?: Info): CompletionResult | null {
  if (answer === null) return null;
  const items = Array.isArray(answer) ? (answer as readonly CompletionItem[]) : (answer as CompletionList).items;
  if (items.length === 0) return null;
  const incomplete = !Array.isArray(answer) && (answer as CompletionList).isIncomplete === true;
  const result: CompletionResult = { from, options: completionOptions(items, info) };
  return incomplete ? result : { ...result, validFor: VALID_FOR_COMPLETE };
}

/** Resolves each item once: the panel of an item that is selected again does not ask again. */
export class ResolveOnce<Item extends object> {
  readonly #ask: (item: Item) => Promise<Item>;
  readonly #resolved = new Map<Item, Promise<Item | null>>();

  constructor(ask: (item: Item) => Promise<Item>) {
    this.#ask = ask;
  }

  /** The resolved item; null when the server could not resolve it. */
  resolve(item: Item): Promise<Item | null> {
    let found = this.#resolved.get(item);
    if (found === undefined) {
      found = this.#ask(item).catch(() => null);
      this.#resolved.set(item, found);
    }
    return found;
  }
}

/**
 * Which completion an editor has (docs/specs/web-ui.md#autocomplete): none while autocomplete
 * does not apply; the server's where it applies and the file's session is ready; the editor's own
 * from the language support otherwise.
 */
export function completionMode(applies: boolean, sessionReady: boolean): "none" | "editor" | "server" {
  if (!applies) return "none";
  return sessionReady ? "server" : "editor";
}
