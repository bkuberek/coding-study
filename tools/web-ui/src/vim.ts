// Vim keybindings are opt-in, so they are a chunk of their own, fetched when first turned on
// (docs/specs/web-ui.md#keyboard-and-accessibility).
import type { Extension } from "@codemirror/state";
import { Prec } from "@codemirror/state";
import { EditorView } from "@codemirror/view";
import { getCM, Vim, vim } from "@replit/codemirror-vim";

import { type CommandName, runNamedCommand } from "./editor-commands.ts";

/** The keys of LazyVim that code intelligence adds, each running the editor's command of that name. */
const KEYS: readonly { readonly keys: string; readonly action: string; readonly command: CommandName }[] = [
  { keys: "]d", action: "cstudyNextDiagnostic", command: "cursorToNextDiagnostic" },
  { keys: "[d", action: "cstudyPreviousDiagnostic", command: "cursorToPreviousDiagnostic" },
  { keys: "K", action: "cstudyHover", command: "hover" },
  { keys: "gd", action: "cstudyDefinition", command: "definition" },
  { keys: "<C-]>", action: "cstudyDefinitionKey", command: "definition" },
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

/**
 * Vim takes Escape in a DOM handler that runs before every key binding, so what an Escape closes
 * (the hover, and the completion list and signature help) is closed from a handler placed before
 * it; Vim then leaves insert mode in the same press.
 */
const DISMISS: Extension = Prec.highest(
  EditorView.domEventHandlers({
    keydown(event, view) {
      if (event.key === "Escape") runNamedCommand(view, "dismiss");
      return false;
    },
  }),
);

export function vimKeybindings(): Extension {
  mapKeys();
  return [DISMISS, vim()];
}

/**
 * Puts a jump inside the file in Vim's jump list, so `Ctrl-o` goes back to where it started. A
 * jump into another file is Back's (Ctrl-Minus): a jump list holds places of one editor.
 */
export function recordJump(view: EditorView, from: number, to: number): void {
  const cm = getCM(view);
  if (cm === null) return;
  Vim.getVimGlobalState_().jumpList.add(cm, cm.posFromIndex(from), cm.posFromIndex(to));
}
