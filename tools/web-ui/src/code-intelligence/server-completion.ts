/**
 * The page's completion source for a language server (docs/specs/web-ui.md#autocomplete), written
 * against `@codemirror/autocomplete`: it asks on a word character, on a trigger character of the
 * server, and on Ctrl-Space; a newer ask cancels the older with `$/cancelRequest`; and the panel
 * beside the list shows the item resolved by `completionItem/resolve`, once per item.
 */

import { type CompletionContext, type CompletionResult, type CompletionSource, autocompletion, closeCompletion } from "@codemirror/autocomplete";
import { LSPPlugin } from "@codemirror/lsp-client";
import type { Extension } from "@codemirror/state";
import type { Command } from "@codemirror/view";

import { h } from "../page/dom.ts";
import { type CompletionItem, type CompletionList, completionRequest, completionResult, ResolveOnce } from "./completion.ts";
import { documentation } from "./hover.ts";
import { hoverContent } from "./hover-content.ts";
import { signatureHelp } from "./signature.ts";

const WORD = /[\w$]+$/;

/** The panel of an item: its detail as text and its documentation, which the broker rendered. */
function infoNode(item: CompletionItem): Node | null {
  const content = hoverContent(item.documentation);
  if (item.detail === undefined && content === null) return null;
  return h(
    "div",
    { class: "cs-hover cs-info" },
    item.detail === undefined ? null : h("code", { class: "cs-detail" }, item.detail),
    content === null ? null : documentation(content),
  );
}

async function ask(context: CompletionContext): Promise<CompletionResult | null> {
  const plugin = context.view === undefined ? null : LSPPlugin.get(context.view);
  const provider = plugin?.client.serverCapabilities?.completionProvider;
  if (plugin === null || provider === undefined) return null;
  const { client, uri } = plugin;
  const word = context.matchBefore(WORD);
  const before = context.state.sliceDoc(Math.max(0, context.pos - 1), context.pos);
  const request = completionRequest({ explicit: context.explicit, word: word?.text ?? "", before, triggers: provider.triggerCharacters ?? [] });
  if (request === null) return null;
  client.sync();
  const params = { textDocument: { uri }, position: plugin.toPosition(context.pos), context: request };
  context.addEventListener("abort", () => client.cancelRequest(params));
  const answer = await client.request<unknown, CompletionList | readonly CompletionItem[] | null>("textDocument/completion", params);
  if (context.aborted) return null;
  // The items go back to the server exactly as received: the broker checks what it sent.
  const resolver = new ResolveOnce<CompletionItem>((item) => client.request<unknown, CompletionItem>("completionItem/resolve", item));
  const from = request.triggerCharacter === undefined && word !== null ? word.from : context.pos;
  return completionResult(answer, from, async (item) => {
    const resolved = provider.resolveProvider === true ? await resolver.resolve(item) : item;
    return resolved === null ? null : infoNode(resolved);
  });
}

/** The server's completion source: errors are the session's to show, so the list just does not come. */
export const serverSource: CompletionSource = (context) => ask(context).catch(() => null);

/**
 * The server's completion and signature help in an editor. The editor's own completion
 * (`completion()` in `setup.ts`) stays in its compartment and keeps its keys; this replaces its
 * sources while it is in the editor, which the page does only while autocomplete applies and the
 * file's session is ready.
 */
export function serverAutocomplete(): Extension {
  return [autocompletion({ override: [serverSource] }), signatureHelp()];
}

/** Closes the completion list, if it is open. */
export const closeList: Command = (view) => closeCompletion(view);
