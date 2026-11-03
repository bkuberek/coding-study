/**
 * Commands the editor's extensions offer by name, so a module that cannot import them can still
 * run them: Vim's keys (`src/vim.ts`, a chunk of its own) run the diagnostic commands of the
 * editor and the go to definition, Back and hover of the code-intelligence chunk, which an
 * editor has only while code intelligence applies to its file.
 */
import { EditorState, Facet } from "@codemirror/state";
import type { Command, EditorView } from "@codemirror/view";

export type CommandName = "cursorToNextDiagnostic" | "cursorToPreviousDiagnostic" | "definition" | "back" | "hover";

export type NamedCommands = Partial<Record<CommandName, Command>>;

export const namedCommands = Facet.define<NamedCommands, NamedCommands>({
  combine: (provided) => Object.assign({}, ...provided),
});

/** The command an editor's state provides under `name`, if any. */
export function namedCommand(state: EditorState, name: CommandName): Command | undefined {
  return state.facet(namedCommands)[name];
}

/** Runs the command of that name; false when the editor has none or the command did not apply. */
export function runNamedCommand(view: EditorView, name: CommandName): boolean {
  return namedCommand(view.state, name)?.(view) ?? false;
}
