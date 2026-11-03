/**
 * Signature help (docs/specs/web-ui.md#autocomplete): the page's own tooltip, not
 * `@codemirror/lsp-client`'s, which renders documentation with `marked`. It opens when a trigger
 * character is typed (`(` and `,` in a call) and on Cmd or Ctrl-Shift-Space, follows the active
 * parameter as the cursor moves through the call, and closes when the server finds the cursor
 * outside it, when the cursor goes back before where it opened, and on Escape.
 */

import { currentCompletions } from "@codemirror/autocomplete";
import { LSPPlugin } from "@codemirror/lsp-client";
import { type Extension, Prec, StateEffect, StateField } from "@codemirror/state";
import { type Command, EditorView, keymap, showTooltip, type Tooltip, ViewPlugin, type ViewUpdate } from "@codemirror/view";

import { h } from "../page/dom.ts";
import { documentation } from "./hover.ts";
import { hoverContent } from "./hover-content.ts";

export interface ParameterInformation {
  readonly label: string | readonly [number, number];
  readonly documentation?: unknown;
}

export interface SignatureInformation {
  readonly label: string;
  readonly documentation?: unknown;
  readonly parameters?: readonly ParameterInformation[];
  readonly activeParameter?: number | null | undefined;
}

export interface SignatureHelp {
  readonly signatures: readonly SignatureInformation[];
  readonly activeSignature?: number | null | undefined;
  readonly activeParameter?: number | null | undefined;
}

/** The signature to show and the index of its active parameter, null when none is. */
export function activeSignature(help: SignatureHelp): { signature: SignatureInformation; parameter: number | null } | null {
  const signature = help.signatures[help.activeSignature ?? 0] ?? help.signatures[0];
  if (signature === undefined) return null;
  const chosen = signature.activeParameter === undefined ? help.activeParameter : signature.activeParameter;
  const index = chosen === undefined ? 0 : chosen;
  const parameter = index !== null && index >= 0 && index < (signature.parameters?.length ?? 0) ? index : null;
  return { signature, parameter };
}

/** The label cut at the active parameter, which is bold; a parameter the label does not hold marks nothing. */
export function labelParts(signature: SignatureInformation, parameter: number | null): { before: string; active: string; after: string } {
  const whole = { before: signature.label, active: "", after: "" };
  const label = parameter === null ? undefined : signature.parameters?.[parameter]?.label;
  if (label === undefined) return whole;
  const [start, end] = typeof label === "string" ? span(signature.label, label) : label;
  if (start < 0 || end > signature.label.length || start >= end) return whole;
  return { before: signature.label.slice(0, start), active: signature.label.slice(start, end), after: signature.label.slice(end) };
}

function span(label: string, parameter: string): [number, number] {
  const start = label.indexOf(parameter);
  return [start, start + parameter.length];
}

const PAIRS = ["()", "[]", "{}"];

/**
 * The trigger character just typed: what was inserted, when it is one character and a trigger, or
 * a bracket with its closing bracket, as closing brackets inserts it.
 */
export function typedTrigger(inserted: string, triggers: readonly string[]): string | null {
  const typed = PAIRS.includes(inserted) ? inserted.slice(0, 1) : inserted;
  return typed.length === 1 && triggers.includes(typed) ? typed : null;
}

const DEBOUNCE_MS = 80;
const INVOKED = 1;
const TRIGGER_CHARACTER = 2;
const CONTENT_CHANGE = 3;
const VIM_CLASS = "cm-vimMode";

interface Shown {
  readonly tooltip: Tooltip;
}

const setShown = StateEffect.define<Shown | null>();

const shownField = StateField.define<Shown | null>({
  create: () => null,
  update(shown, transaction) {
    for (const effect of transaction.effects) if (effect.is(setShown)) return effect.value;
    if (shown === null || !transaction.docChanged) return shown;
    return { tooltip: { ...shown.tooltip, pos: transaction.changes.mapPos(shown.tooltip.pos, -1) } };
  },
  provide: (field) => showTooltip.from(field, (shown) => shown?.tooltip ?? null),
});

function element(help: SignatureHelp): HTMLElement | null {
  const found = activeSignature(help);
  if (found === null) return null;
  const { signature, parameter } = found;
  const parts = labelParts(signature, parameter);
  const label = h("code", { class: "cs-signature-label" }, parts.before, parts.active === "" ? null : h("strong", { class: "cs-active-parameter" }, parts.active), parts.after);
  const parameterDoc = parameter === null ? null : hoverContent(signature.parameters?.[parameter]?.documentation);
  const signatureDoc = hoverContent(signature.documentation);
  return h(
    "div",
    { class: "cs-hover cs-signature", tabindex: 0, role: "region", "aria-label": "Signature help" },
    label,
    parameterDoc === null ? null : documentation(parameterDoc),
    signatureDoc === null ? null : documentation(signatureDoc),
  );
}

function triggersOf(view: EditorView): { all: readonly string[]; provided: boolean } {
  const provider = LSPPlugin.get(view)?.client.serverCapabilities?.signatureHelpProvider;
  return { all: [...(provider?.triggerCharacters ?? []), ...(provider?.retriggerCharacters ?? [])], provided: provider !== undefined };
}

class SignaturePlugin {
  readonly #view: EditorView;
  #token = 0;
  #timer: ReturnType<typeof setTimeout> | undefined;

  constructor(view: EditorView) {
    this.#view = view;
  }

  update(update: ViewUpdate): void {
    if (!update.docChanged && !update.selectionSet) return;
    const open = update.state.field(shownField);
    const typed = update.transactions.some((transaction) => transaction.isUserEvent("input.type")) ? lastInserted(update) : "";
    const trigger = typedTrigger(typed, triggersOf(update.view).all);
    if (trigger !== null) {
      this.#ask({ triggerKind: TRIGGER_CHARACTER, triggerCharacter: trigger, isRetrigger: open !== null });
    } else if (open !== null) {
      // A view is not to be updated from inside an update.
      if (update.state.selection.main.head < open.tooltip.pos) queueMicrotask(() => this.#close());
      else this.#later({ triggerKind: CONTENT_CHANGE, isRetrigger: true });
    }
  }

  destroy(): void {
    clearTimeout(this.#timer);
    this.#token += 1;
  }

  /** Asks the server for the signature at the cursor; `INVOKED` for the key. */
  ask(context: { triggerKind: number; triggerCharacter?: string; isRetrigger: boolean }): void {
    this.#ask(context);
  }

  #later(context: { triggerKind: number; isRetrigger: boolean }): void {
    clearTimeout(this.#timer);
    this.#timer = setTimeout(() => this.#ask(context), DEBOUNCE_MS);
  }

  #ask(context: { triggerKind: number; triggerCharacter?: string; isRetrigger: boolean }): void {
    const plugin = LSPPlugin.get(this.#view);
    if (plugin === null || !triggersOf(this.#view).provided) return;
    const token = ++this.#token;
    const { client, uri } = plugin;
    client.sync();
    client
      .request<unknown, SignatureHelp | null>("textDocument/signatureHelp", {
        textDocument: { uri },
        position: plugin.toPosition(this.#view.state.selection.main.head),
        context,
      })
      .then(
        (help) => {
          if (token === this.#token) this.#show(help);
        },
        () => {
          if (token === this.#token) this.#close();
        },
      );
  }

  #show(help: SignatureHelp | null): void {
    const dom = help === null ? null : element(help);
    if (dom === null) {
      this.#close();
      return;
    }
    const open = this.#view.state.field(shownField);
    const pos = open?.tooltip.pos ?? this.#view.state.selection.main.head;
    this.#view.dispatch({ effects: setShown.of({ tooltip: { pos, above: true, create: () => ({ dom }) } }) });
  }

  #close(): void {
    clearTimeout(this.#timer);
    this.#token += 1;
    if (this.#view.state.field(shownField) !== null) this.#view.dispatch({ effects: setShown.of(null) });
  }

  close(): boolean {
    const open = this.#view.state.field(shownField) !== null;
    this.#close();
    return open;
  }
}

function lastInserted(update: ViewUpdate): string {
  let text = "";
  update.changes.iterChanges((_fromA, _toA, _fromB, _toB, inserted) => {
    text = inserted.toString();
  });
  return text;
}

const plugin = ViewPlugin.fromClass(SignaturePlugin);

/** Opens the signature help at the cursor; not in Vim's normal mode, which inserts no text. */
export const showSignatureHelp: Command = (view) => {
  if (view.scrollDOM.classList.contains(VIM_CLASS)) return false;
  const instance = view.plugin(plugin);
  if (instance === null) return false;
  instance.ask({ triggerKind: INVOKED, isRetrigger: view.state.field(shownField) !== null });
  return true;
};

/** Closes the signature help, if it is open. */
export const closeSignature: Command = (view) => view.plugin(plugin)?.close() ?? false;

/**
 * Escape closes a list that shows first, which the completion keymap does. A completion that is
 * only pending (no list shows) takes the key too and leaves the signature help open, and the
 * editor's completion sits in a compartment before this one, so its key binding comes first: a
 * key handler of the DOM, which runs before any key binding, closes the signature help.
 */
const escape = EditorView.domEventHandlers({
  keydown(event, view) {
    if (event.key !== "Escape" || currentCompletions(view.state).length > 0 || !closeSignature(view)) return false;
    event.preventDefault();
    return true;
  },
});

export function signatureHelp(): Extension {
  return [
    shownField,
    plugin,
    Prec.highest(escape),
    keymap.of([{ key: "Mod-Shift-Space", run: showSignatureHelp, preventDefault: true }]),
  ];
}
