/**
 * The editor's standing extensions (docs/specs/web-ui.md#editor): `basicSetup`'s parts, copied as
 * its documentation advises, with two changes. Adding a cursor is Alt-Shift-click for every user,
 * and completion is not here: `completion` holds it in a compartment of the editor, so that the
 * `autocomplete` preference governs all of it.
 */
import { closeBrackets, closeBracketsKeymap, autocompletion } from "@codemirror/autocomplete";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import {
  bracketMatching,
  defaultHighlightStyle,
  foldGutter,
  foldKeymap,
  indentOnInput,
  syntaxHighlighting,
} from "@codemirror/language";
import { lintKeymap } from "@codemirror/lint";
import { highlightSelectionMatches, searchKeymap } from "@codemirror/search";
import { EditorState, type Extension } from "@codemirror/state";
import {
  crosshairCursor,
  drawSelection,
  dropCursor,
  EditorView,
  highlightActiveLine,
  highlightActiveLineGutter,
  highlightSpecialChars,
  keymap,
  lineNumbers,
  rectangularSelection,
} from "@codemirror/view";

/** The modifier keys of a pointer event. */
export interface Modifiers {
  readonly altKey: boolean;
  readonly shiftKey: boolean;
  readonly metaKey: boolean;
  readonly ctrlKey: boolean;
}

/**
 * Whether a click adds a cursor: Alt-Shift-click (Option-Shift-click). Cmd-click and Ctrl-click
 * never do; they are a plain click, or go to the definition where code intelligence applies.
 */
export function addsCursor(event: Modifiers): boolean {
  return event.altKey && event.shiftKey;
}

export const editorSetup: Extension = [
  lineNumbers(),
  highlightActiveLineGutter(),
  highlightSpecialChars(),
  history(),
  foldGutter(),
  drawSelection(),
  dropCursor(),
  EditorState.allowMultipleSelections.of(true),
  EditorView.clickAddsSelectionRange.of(addsCursor),
  indentOnInput(),
  syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
  bracketMatching(),
  closeBrackets(),
  rectangularSelection(),
  crosshairCursor(),
  highlightActiveLine(),
  highlightSelectionMatches(),
  keymap.of([...closeBracketsKeymap, ...defaultKeymap, ...searchKeymap, ...historyKeymap, ...foldKeymap, ...lintKeymap]),
];

/**
 * CodeMirror's completion, with its key bindings, while the `autocomplete` preference applies;
 * nothing otherwise: no list as you type or on Ctrl-Space. Closing brackets is not completion and
 * stays in `editorSetup`.
 */
export function completion(applies: boolean): Extension {
  return applies ? autocompletion() : [];
}
