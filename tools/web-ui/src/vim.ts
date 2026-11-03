// Vim keybindings are opt-in, so they are a chunk of their own, fetched when first turned on
// (docs/specs/web-ui.md#keyboard-and-accessibility).
import type { Extension } from "@codemirror/state";
import { Vim, vim } from "@replit/codemirror-vim";

import { type CommandName, runNamedCommand } from "./editor-commands.ts";

/** The keys of LazyVim that code intelligence adds, each running the editor's command of that name. */
const KEYS: readonly { readonly keys: string; readonly action: string; readonly command: CommandName }[] = [
  { keys: "]d", action: "cstudyNextDiagnostic", command: "cursorToNextDiagnostic" },
  { keys: "[d", action: "cstudyPreviousDiagnostic", command: "cursorToPreviousDiagnostic" },
];

let mapped = false;

/**
 * Vim's keys are global to the page, so they are mapped once. In an editor without the command
 * (code intelligence does not apply to its file) a key does nothing.
 */
function mapKeys(): void {
  if (mapped) return;
  mapped = true;
  for (const { keys, action, command } of KEYS) {
    Vim.defineAction(action, (cm) => {
      runNamedCommand(cm.cm6, command);
    });
    Vim.mapCommand(keys, "action", action, {}, { context: "normal" });
  }
}

export function vimKeybindings(): Extension {
  mapKeys();
  return vim();
}
