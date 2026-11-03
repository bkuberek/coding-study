/**
 * While Cmd (macOS) or Ctrl is held over the editor, the word under the pointer is underlined and
 * the pointer is a hand (docs/specs/web-ui.md#go-to-definition). Nothing is requested until the
 * click: the underline says only that the click will try.
 */

import { type Extension, StateEffect, StateField } from "@codemirror/state";
import { Decoration, type DecorationSet, EditorView, ViewPlugin } from "@codemirror/view";

import { isDefinitionClick } from "./navigation.ts";

interface Word {
  readonly from: number;
  readonly to: number;
}

const setWord = StateEffect.define<Word | null>();
const MARK = Decoration.mark({ class: "cs-definition-link" });

const wordField = StateField.define<Word | null>({
  create: () => null,
  update(word, transaction) {
    for (const effect of transaction.effects) if (effect.is(setWord)) return effect.value;
    return word !== null && transaction.docChanged ? null : word;
  },
  provide: (field) => [
    EditorView.decorations.from(field, (word): DecorationSet =>
      word === null ? Decoration.none : Decoration.set([MARK.range(word.from, word.to)]),
    ),
    EditorView.contentAttributes.from(field, (word) => (word === null ? {} : { class: "cs-link-ready" })),
  ],
});

/** Whether `key` is the one that makes a click a jump on this platform. */
export function isJumpKey(key: string, mac: boolean): boolean {
  return key === (mac ? "Meta" : "Control");
}

export function definitionLink(mac: boolean): Extension {
  const watch = ViewPlugin.fromClass(
    class {
      readonly view: EditorView;
      #pointer: { x: number; y: number } | null = null;
      #held = false;

      constructor(view: EditorView) {
        this.view = view;
        window.addEventListener("keydown", this.#onKey);
        window.addEventListener("keyup", this.#onKey);
        window.addEventListener("blur", this.#onBlur);
        view.dom.addEventListener("mousemove", this.#onMove);
        view.dom.addEventListener("mouseleave", this.#onLeave);
      }

      destroy(): void {
        window.removeEventListener("keydown", this.#onKey);
        window.removeEventListener("keyup", this.#onKey);
        window.removeEventListener("blur", this.#onBlur);
        this.view.dom.removeEventListener("mousemove", this.#onMove);
        this.view.dom.removeEventListener("mouseleave", this.#onLeave);
      }

      readonly #onKey = (event: KeyboardEvent): void => {
        if (!isJumpKey(event.key, mac)) return;
        this.#held = event.type === "keydown";
        this.#show();
      };

      readonly #onBlur = (): void => {
        this.#held = false;
        this.#show();
      };

      readonly #onMove = (event: MouseEvent): void => {
        this.#pointer = { x: event.clientX, y: event.clientY };
        this.#held = isDefinitionClick(event, mac);
        this.#show();
      };

      readonly #onLeave = (): void => {
        this.#pointer = null;
        this.#show();
      };

      #show(): void {
        const pos = this.#held && this.#pointer !== null ? this.view.posAtCoords(this.#pointer) : null;
        const word = pos === null ? null : this.view.state.wordAt(pos);
        const shown = word === null ? null : { from: word.from, to: word.to };
        const current = this.view.state.field(wordField);
        if (shown?.from === current?.from && shown?.to === current?.to) return;
        this.view.dispatch({ effects: setWord.of(shown) });
      }
    },
  );
  return [wordField, watch];
}
