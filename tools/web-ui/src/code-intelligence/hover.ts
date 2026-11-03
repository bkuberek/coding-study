/**
 * Hover documentation (docs/specs/web-ui.md#hover): the page's own tooltip, not
 * `@codemirror/lsp-client`'s, which renders Markdown in the browser. It shows the `cstudy-html`
 * the broker rendered, in the same box as a diagnostic under the pointer (the lint extension's
 * hover tooltip comes first in the box). It opens with the pointer at rest, and from the keyboard
 * with Cmd or Ctrl-K, Cmd or Ctrl-I, and then a screen reader hears its first paragraph.
 */

import { LSPPlugin } from "@codemirror/lsp-client";
import { type Extension, Prec } from "@codemirror/state";
import {
  activateHover,
  closeHoverTooltips,
  type Command,
  type EditorView,
  hasHoverTooltips,
  hoverTooltip,
  keymap,
  type Tooltip,
} from "@codemirror/view";

import { h, rendered } from "../page/dom.ts";
import { type HoverContent, firstParagraph, hoverContent } from "./hover-content.ts";
import type { Position } from "./live-diagnostics.ts";

interface HoverAnswer {
  readonly contents: unknown;
  readonly range?: { readonly start: Position; readonly end: Position };
}

interface Found {
  readonly content: HoverContent;
  readonly from: number;
  readonly to: number;
}

const NOTHING_TO_SHOW = "no documentation here";

/** The editors a hover was just opened in from the keyboard, whose answer the live region reads. */
const fromKeyboard = new WeakSet<EditorView>();

async function ask(plugin: LSPPlugin, pos: number): Promise<Found | null> {
  const { client, uri } = plugin;
  client.sync();
  return client.withMapping(async (mapping) => {
    const answer = await client.request<unknown, HoverAnswer | null>("textDocument/hover", {
      textDocument: { uri },
      position: plugin.toPosition(pos),
    });
    const content = answer === null ? null : hoverContent(answer.contents);
    if (answer === null || content === null) return null;
    if (answer.range === undefined) return { content, from: pos, to: pos };
    return { content, from: mapping.mapPosition(uri, answer.range.start), to: mapping.mapPosition(uri, answer.range.end) };
  });
}

function element(content: HoverContent): HTMLElement {
  const body = content.kind === "html" ? rendered(content.html, "cs-doc") : h("pre", { class: "doc-plain" }, content.text);
  // Focusable, so the keyboard scrolls documentation too long for the box (WCAG 2.1.1).
  return h("div", { class: "cs-hover", tabindex: 0, role: "region", "aria-label": "Documentation" }, body);
}

function spoken(content: HoverContent): string {
  return content.kind === "html" ? firstParagraph(content.html) : (content.text.split(/\n\s*\n/)[0] ?? "").replace(/\s+/g, " ").trim();
}

/** The hover tooltip and the keys that open and close it. `announce` is the page's polite live region. */
export function hover(announce: (message: string) => void): Extension {
  const source = async (view: EditorView, pos: number): Promise<Tooltip | null> => {
    const plugin = LSPPlugin.get(view);
    const keyboard = fromKeyboard.delete(view);
    if (plugin === null) return null;
    const found = await ask(plugin, pos).catch(() => null);
    if (keyboard) announce(found === null ? NOTHING_TO_SHOW : spoken(found.content) || NOTHING_TO_SHOW);
    if (found === null) return null;
    return { pos: found.from, end: found.to, above: true, create: () => ({ dom: element(found.content) }) };
  };
  return [
    // After the lint extension's own hover, so a diagnostic is above the documentation in the box.
    Prec.lowest(hoverTooltip(source)),
    keymap.of([
      { key: "Mod-k Mod-i", run: showHover, preventDefault: true },
      { key: "Escape", run: closeHover },
    ]),
  ];
}

/**
 * Opens the hover at the cursor, and keeps it open until an edit or a move of the cursor. A
 * transaction that sets the selection where it already is (Vim does, as it handles a key) does not close it.
 */
export const showHover: Command = (view) => {
  if (LSPPlugin.get(view) === null) return false;
  fromKeyboard.add(view);
  const head = view.state.selection.main.head;
  activateHover(view, head, 1, {
    until: (transaction) => transaction.docChanged || transaction.newSelection.main.head !== head,
  });
  return true;
};

/** Closes the hover tooltips, if any is open. */
export const closeHover: Command = (view) => {
  if (!hasHoverTooltips(view.state)) return false;
  view.dispatch({ effects: closeHoverTooltips });
  return true;
};
