/**
 * What an editor gets from a session (docs/specs/web-ui.md#code-intelligence-in-the-editor): the
 * client's plugin, which opens the file with the server and closes it with the editor, and the
 * page's own hover (Escape closes it, also under Vim, which takes Escape before any keymap). The commands the extension provides are also found by name (Vim's keys).
 */

import type { Extension } from "@codemirror/state";

import { namedCommands } from "../editor-commands.ts";
import { closeHover, hover, showHover } from "./hover.ts";
import type { Session } from "./session.ts";

export interface EditorHooks {
  /** Read by screen readers without moving the focus. */
  readonly announce: (message: string) => void;
}

export function intelligenceExtension(session: Session, uri: string, languageId: string, hooks: EditorHooks): Extension {
  return [session.plugin(uri, languageId), hover(hooks.announce), namedCommands.of({ hover: showHover, dismiss: closeHover })];
}
