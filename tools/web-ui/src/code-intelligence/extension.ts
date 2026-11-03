/**
 * What an editor gets from a session (docs/specs/web-ui.md#code-intelligence-in-the-editor): the
 * client's plugin, which opens the file with the server and closes it with the editor, and the
 * page's own hover and go to definition. The commands the extension provides are also found by
 * name (Vim's keys). Escape closes the hover, also under Vim, which takes Escape before any keymap.
 */

import type { Extension } from "@codemirror/state";

import { namedCommands } from "../editor-commands.ts";
import { backCommand, backKeys, definition, type Navigator } from "./definition.ts";
import { closeHover, hover, showHover } from "./hover.ts";
import type { Session } from "./session.ts";

export interface EditorHooks {
  /** Read by screen readers without moving the focus. */
  readonly announce: (message: string) => void;
  /** The page's tabs, which a jump opens. */
  readonly navigator: Navigator;
  /** The file's path in the attempt's tree. */
  readonly path: string;
}

export function intelligenceExtension(session: Session, uri: string, languageId: string, hooks: EditorHooks): Extension {
  return [
    session.plugin(uri, languageId),
    hover(hooks.announce),
    namedCommands.of({ hover: showHover, dismiss: closeHover }),
    definition({ tab: { kind: "attempt", path: hooks.path }, rootUri: session.rootUri, navigator: hooks.navigator }),
  ];
}

/** What the read-only tab of a library file gets: Back, to where the jump into it started. */
export function libraryNavigation(navigator: Navigator): Extension {
  const back = backCommand(navigator);
  return [backKeys(back), namedCommands.of({ back })];
}
