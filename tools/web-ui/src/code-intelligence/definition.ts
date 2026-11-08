/**
 * Go to definition and Back (docs/specs/web-ui.md#go-to-definition). `@codemirror/lsp-client`'s
 * own `jumpToDefinition` is not used: it reads `uri` and `range` of the first location, which a
 * `LocationLink` (what the broker lets servers send) does not have, and it can show neither the
 * library tab, nor a refusal, nor `no definition found`.
 */

import { LSPPlugin } from "@codemirror/lsp-client";
import { type Extension, Prec } from "@codemirror/state";
import { type Command, EditorView, keymap } from "@codemirror/view";

import type { Editor } from "../editor.ts";
import { namedCommands } from "../editor-commands.ts";
import { definitionLink } from "./definition-link.ts";
import { lspOffset } from "./live-diagnostics.ts";
import { classifyTarget, definitionTarget, type DefinitionTarget, isDefinitionClick, JumpStack, linkTarget, type Origin, refusalNote, type TabRef } from "./navigation.ts";
import { closeNote, noteExtension, showNote } from "./note.ts";

/** A file of a library that the broker read for the page. */
export interface LibraryFile {
  readonly uri: string;
  /** The path as the broker shows it: relative to the workspace, else absolute with `~`. */
  readonly path: string;
  readonly text: string;
}

/** What go to definition needs of the page's tabs. */
export interface Navigator {
  /** The paths of the attempt's tree. */
  paths(): Promise<ReadonlySet<string>>;
  /** Opens the attempt's file in a tab, or brings its tab forward; null when it cannot. */
  openFile(path: string): Promise<Editor | null>;
  /** Opens a read-only tab for the library file, or brings forward and refreshes the one it has. */
  openLibrary(file: LibraryFile): Promise<Editor | null>;
  /** Brings the library tab for the URI forward; null when it was closed. */
  showLibrary(uri: string): Editor | null;
  /** The status bar says `text` for a few seconds. */
  say(text: string): void;
}

export const NO_DEFINITION = "no definition found";

/** The last places a jump started in, for all the page's editors. */
export const jumps = new JumpStack();

const MAC = /^Mac/.test(typeof navigator === "undefined" ? "" : navigator.platform);
/** The class the Vim extension puts on the scroller while Vim is on and the mode is not insert. */
const VIM_CLASS = "cm-vimMode";

/** Where an editor's jumps start, and the page's tabs they go to. */
export interface JumpContext {
  readonly tab: TabRef;
  readonly rootUri: string;
  readonly navigator: Navigator;
}

/** The commands of an editor with a session: go to definition and Back. */
export function definitionCommands(context: JumpContext): { goTo: Command; back: Command } {
  return {
    goTo: (view) => {
      if (LSPPlugin.get(view) === null) return false;
      void goToDefinition(view, context).catch((error: unknown) => showNote(view, refusalNote(error, 0)));
      return true;
    },
    back: (view) => {
      void goBack(context.navigator);
      return true;
    },
  };
}

/** Back alone, for the tab of a library file, which has no session to ask. */
export function backCommand(navigator: Navigator): Command {
  return (view) => {
    void goBack(navigator);
    return true;
  };
}

/**
 * What an editor with a session gets: F12, Cmd or Ctrl-click, the underline while the key is
 * held, Ctrl-Minus and the notes.
 */
export function definition(context: JumpContext): Extension {
  const { goTo, back } = definitionCommands(context);
  return [
    noteExtension,
    definitionLink(MAC),
    EditorView.domEventHandlers({
      mousedown(event, view) {
        if (event.button !== 0 || !isDefinitionClick(event, MAC)) return false;
        const pos = view.posAtCoords({ x: event.clientX, y: event.clientY });
        if (pos === null) return false;
        event.preventDefault();
        view.dispatch({ selection: { anchor: pos } });
        return goTo(view);
      },
    }),
    keymap.of([{ key: "F12", run: goTo, preventDefault: true }]),
    backKeys(back),
    namedCommands.of({ definition: goTo, back }),
  ];
}

/** Ctrl-Minus, which the editor takes for itself while it has the focus. */
export function backKeys(back: Command): Extension {
  return Prec.high(keymap.of([{ key: "Ctrl--", run: back, preventDefault: true }]));
}

async function goToDefinition(view: EditorView, context: JumpContext): Promise<void> {
  const plugin = LSPPlugin.get(view);
  if (plugin === null) return;
  const head = view.state.selection.main.head;
  const { client, uri } = plugin;
  client.sync();
  closeNote(view);
  await client.withMapping(async (mapping) => {
    const answer = await client.request<unknown, unknown>("textDocument/definition", {
      textDocument: { uri },
      position: plugin.toPosition(head),
    });
    const target = definitionTarget(answer);
    if (target === null) {
      context.navigator.say(NO_DEFINITION);
      return;
    }
    await jumpTo(view, context, { tab: context.tab, head }, target, (place) => mapping.mapPosition(uri, place));
  });
}

/**
 * Follows a link of hover documentation (docs/specs/web-ui.md#hover), as a definition is followed:
 * within the file, into the attempt's tab, or into a library tab, at the line the link names.
 */
export function followLink(view: EditorView, context: JumpContext, href: string): void {
  const plugin = LSPPlugin.get(view);
  if (plugin === null) return;
  const origin: Origin = { tab: context.tab, head: view.state.selection.main.head };
  const offsetOf = (place: DefinitionTarget): number => lspOffset(view.state.doc, place);
  void jumpTo(view, context, origin, linkTarget(href), offsetOf).catch((error: unknown) => showNote(view, refusalNote(error, 0)));
}

/** Goes to `target` from `origin`; `offsetOf` places a target in the file itself. */
async function jumpTo(view: EditorView, context: JumpContext, origin: Origin, target: DefinitionTarget, offsetOf: (target: DefinitionTarget) => number): Promise<void> {
  const plugin = LSPPlugin.get(view);
  if (plugin === null) return;
  const where = classifyTarget(target.uri, plugin.uri, context.rootUri, await context.navigator.paths());
  if (where.kind === "same") {
    jumps.push(origin);
    moveInside(view, origin.head, offsetOf(target));
  } else if (where.kind === "attempt") {
    const editor = await context.navigator.openFile(where.path);
    if (editor === null) return;
    jumps.push(origin);
    editor.jumpTo(target.line + 1, target.character + 1);
  } else {
    await openLibrary(view, context.navigator, origin, target);
  }
}

async function openLibrary(view: EditorView, navigator: Navigator, origin: Origin, target: DefinitionTarget): Promise<void> {
  const plugin = LSPPlugin.get(view);
  if (plugin === null) return;
  let file: LibraryFile;
  try {
    file = await plugin.client.request<unknown, LibraryFile>("cstudy/libraryFile", { uri: target.uri });
  } catch (error) {
    showNote(view, refusalNote(error, target.line));
    return;
  }
  const editor = await navigator.openLibrary(file);
  if (editor === null) return;
  jumps.push(origin);
  editor.jumpTo(target.line + 1, target.character + 1);
}

/** Moves the cursor within the file, scrolled into view; Vim's jump list hears of it. */
function moveInside(view: EditorView, from: number, to: number): void {
  view.dispatch({ selection: { anchor: to }, effects: EditorView.scrollIntoView(to, { y: "center" }), userEvent: "select.definition" });
  view.focus();
  if (view.scrollDOM.classList.contains(VIM_CLASS)) void import("../vim.ts").then((vim) => vim.recordJump(view, from, to));
}

async function goBack(navigator: Navigator): Promise<void> {
  const origin = jumps.pop((found) => found.tab.kind === "attempt" || navigator.showLibrary(found.tab.uri) !== null);
  if (origin === null) return;
  const editor = origin.tab.kind === "attempt" ? await navigator.openFile(origin.tab.path) : navigator.showLibrary(origin.tab.uri);
  if (editor === null) return;
  const anchor = Math.min(origin.head, editor.view.state.doc.length);
  editor.view.dispatch({ selection: { anchor }, effects: EditorView.scrollIntoView(anchor, { y: "center" }) });
  editor.focus();
}
