/**
 * What an editor gets from a session (docs/specs/web-ui.md#code-intelligence-in-the-editor): the
 * client's plugin, which opens the file with the server and closes it with the editor, and the
 * page's own hover, go to definition and, in a slot of its own, the server's completion and
 * signature help. The commands the extension provides are also found by name (Vim's keys).
 * Escape closes the hover, the list and the signature help, also under Vim, which takes Escape
 * before any keymap.
 */

import { Compartment, type Extension, type StateEffect } from "@codemirror/state";

import { namedCommands } from "../editor-commands.ts";
import { completionMode } from "./completion.ts";
import { backCommand, backKeys, definition, followLink, type JumpContext, type Navigator } from "./definition.ts";
import { closeHover, hover, showHover } from "./hover.ts";
import { closeList, serverAutocomplete } from "./server-completion.ts";
import type { Session } from "./session.ts";
import { closeSignature } from "./signature.ts";

export interface EditorHooks {
  /** Read by screen readers without moving the focus. */
  readonly announce: (message: string) => void;
  /** The page's tabs, which a jump opens. */
  readonly navigator: Navigator;
  /** The file's path in the attempt's tree. */
  readonly path: string;
}

/** An editor's extension, and the change that sets its completion for the preferences and the session. */
export interface Intelligence {
  readonly extension: Extension;
  /** The effect that gives the editor the server's completion and signature help, or takes them away. */
  completion(autocompleteApplies: boolean, sessionReady: boolean): StateEffect<unknown>;
}

const dismiss = (view: Parameters<typeof closeHover>[0]): boolean => {
  const closed = [closeHover(view), closeList(view), closeSignature(view)];
  return closed.some(Boolean);
};

export function intelligenceExtension(session: Session, uri: string, languageId: string, hooks: EditorHooks): Intelligence {
  const slot = new Compartment();
  const jumps: JumpContext = { tab: { kind: "attempt", path: hooks.path }, rootUri: session.rootUri, navigator: hooks.navigator };
  return {
    extension: [
      session.plugin(uri, languageId),
      hover(hooks.announce, (view, href) => followLink(view, jumps, href)),
      namedCommands.of({ hover: showHover, dismiss }),
      definition(jumps),
      slot.of([]),
    ],
    completion: (applies, ready) => slot.reconfigure(completionMode(applies, ready) === "server" ? serverAutocomplete() : []),
  };
}

/** What the read-only tab of a library file gets: Back, to where the jump into it started. */
export function libraryNavigation(navigator: Navigator): Extension {
  const back = backCommand(navigator);
  return [backKeys(back), namedCommands.of({ back })];
}
