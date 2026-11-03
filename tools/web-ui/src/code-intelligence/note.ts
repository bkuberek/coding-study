/**
 * A note at the cursor (docs/specs/web-ui.md#go-to-definition): why a jump found nothing to open,
 * such as a library file over 4 MiB. It is a tooltip that a screen reader hears (a status), and it
 * closes on the next key or click.
 */

import { type Extension, StateEffect, StateField } from "@codemirror/state";
import { EditorView, showTooltip, type Tooltip } from "@codemirror/view";

import { h } from "../page/dom.ts";

const setNote = StateEffect.define<Tooltip | null>();

const noteField = StateField.define<Tooltip | null>({
  create: () => null,
  update(note, transaction) {
    for (const effect of transaction.effects) if (effect.is(setNote)) return effect.value;
    return transaction.docChanged ? null : note;
  },
  provide: (field) => showTooltip.from(field),
});

/** The field behind the note, and the key or click that closes it (and goes on to do what it does). */
export const noteExtension: Extension = [
  noteField,
  EditorView.domEventHandlers({
    keydown: (_event, view) => closeNote(view),
    mousedown: (_event, view) => closeNote(view),
  }),
];

/** Shows `text` at the cursor until the next key or click. */
export function showNote(view: EditorView, text: string): void {
  const pos = view.state.selection.main.head;
  const note: Tooltip = { pos, above: true, create: () => ({ dom: h("div", { class: "cs-note", role: "status" }, text) }) };
  view.dispatch({ effects: setNote.of(note) });
}

/** Closes the note, if one is open; false, so an event handler lets the event go on. */
export function closeNote(view: EditorView): false {
  if (view.state.field(noteField) !== null) view.dispatch({ effects: setNote.of(null) });
  return false;
}
