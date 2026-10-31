/**
 * The page's questions about files (docs/specs/web-ui.md#attempt-view): a modal `<dialog>`, which
 * keeps the focus inside, closes with Escape, and gives the focus back to where it was. A question
 * that asks for a name checks it as it is typed and shows the server's refusal in place, so a
 * refused name can be corrected without starting over.
 */

import "./files.css";

import { ApiError } from "./api.ts";
import { command, h } from "./dom.ts";

export interface Confirmation {
  readonly title: string;
  readonly message: string;
  /** The button that does it, such as `Delete`. */
  readonly action: string;
  /** Whether it loses work; the focus then starts on Cancel. */
  readonly destructive: boolean;
  /** The `cstudy` command it matches, named beside it. */
  readonly command?: string;
}

export interface NameField {
  readonly label: string;
  /** Shown before the input: what the name is relative to. */
  readonly prefix: string;
  readonly value: string;
  /** Why a value cannot be used; null when it can. */
  readonly issue: (value: string) => string | null;
}

export interface NameRequest {
  readonly title: string;
  readonly note?: string;
  readonly fields: readonly NameField[];
  readonly action: string;
  /** Does it with the fields' values; answers a refusal to show, or null once done. */
  readonly submit: (values: readonly string[]) => Promise<string | null>;
}

const CONFIRMED = "confirmed";
let dialogs = 0;

/** Resolves true once the action is confirmed, false when the dialog is dismissed. */
export function confirmAction(confirmation: Confirmation): Promise<boolean> {
  const title = h("h2", { class: "dialog-title", id: nextId() }, confirmation.title);
  const cancel = h("button", { type: "button", class: "ghost", autofocus: confirmation.destructive }, "Cancel");
  const confirm = h(
    "button",
    { type: "submit", value: CONFIRMED, class: `button ${confirmation.destructive ? "danger" : "primary"}`, autofocus: !confirmation.destructive },
    confirmation.action,
  );
  const form = h(
    "form",
    { method: "dialog" },
    title,
    h("p", { class: "dialog-message" }, confirmation.message),
    confirmation.command ? h("p", { class: "dialog-command quiet" }, "as ", command(confirmation.command)) : null,
    h("div", { class: "dialog-actions" }, cancel, confirm),
  );
  const dialog = opened(form, title.id);
  cancel.addEventListener("click", () => dialog.close());
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue === CONFIRMED), { once: true });
  });
}

/** Resolves true once `submit` succeeds, false when the dialog is dismissed. */
export function askNames(request: NameRequest): Promise<boolean> {
  const title = h("h2", { class: "dialog-title", id: nextId() }, request.title);
  const issue = h("p", { class: "dialog-issue", id: nextId(), "aria-live": "polite" });
  const inputs = request.fields.map((field) =>
    h("input", { type: "text", value: field.value, spellcheck: "false", autocomplete: "off", autocapitalize: "off", "aria-describedby": issue.id }),
  );
  const submit = h("button", { type: "submit", class: "button primary" }, request.action);
  const cancel = h("button", { type: "button", class: "ghost" }, "Cancel");
  const form = h(
    "form",
    { novalidate: true },
    title,
    request.note ? h("p", { class: "dialog-message quiet" }, request.note) : null,
    ...request.fields.map((field, index) =>
      h("label", { class: "dialog-field" }, h("span", { class: "dialog-label" }, field.label), h("span", { class: "dialog-input" }, field.prefix ? h("span", { class: "dialog-prefix", "aria-hidden": "true" }, field.prefix) : null, inputs[index])),
    ),
    issue,
    h("div", { class: "dialog-actions" }, cancel, submit),
  );
  const dialog = opened(form, title.id);
  const values = () => inputs.map((input) => input.value.trim());
  let typed = false;
  const check = (): string | null => {
    const found = request.fields.map((field, index) => field.issue(values()[index] ?? "")).find((problem) => problem !== null) ?? null;
    issue.textContent = typed ? (found ?? "") : "";
    submit.disabled = found !== null;
    return found;
  };
  for (const input of inputs) {
    input.addEventListener("input", () => {
      typed = true;
      check();
    });
  }
  selectStem(inputs[0]);
  check();
  cancel.addEventListener("click", () => dialog.close());
  return new Promise((resolve) => {
    let done = false;
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      typed = true;
      if (check() !== null) return;
      submit.disabled = true;
      dialog.setAttribute("aria-busy", "true");
      void request
        .submit(values())
        .catch((error: unknown) => messageOf(error))
        .then((refusal) => {
          dialog.removeAttribute("aria-busy");
          if (refusal === null) {
            done = true;
            dialog.close();
            return;
          }
          issue.textContent = refusal;
          submit.disabled = false;
          inputs[0]?.focus();
        });
    });
    dialog.addEventListener("close", () => resolve(done), { once: true });
  });
}

/** The text of a refusal, as the CLI words it. */
export function messageOf(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return error instanceof Error ? error.message : String(error);
}

function opened(form: HTMLFormElement, titleId: string): HTMLDialogElement {
  const dialog = h("dialog", { class: "file-dialog", "aria-labelledby": titleId }, form);
  const returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  dialog.addEventListener(
    "close",
    () => {
      dialog.remove();
      if (returnFocus?.isConnected) returnFocus.focus();
    },
    { once: true },
  );
  document.body.append(dialog);
  dialog.showModal();
  return dialog;
}

/** Selects a file name's stem, as editors do on rename: `ledger` of `bank/ledger.py`. */
function selectStem(input: HTMLInputElement | undefined): void {
  if (!input) return;
  const value = input.value;
  const start = value.lastIndexOf("/") + 1;
  const dot = value.lastIndexOf(".");
  input.focus();
  input.setSelectionRange(start, dot > start ? dot : value.length);
}

function nextId(): string {
  dialogs += 1;
  return `file-dialog-${dialogs}`;
}
