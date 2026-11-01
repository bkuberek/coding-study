/**
 * The page's modal dialogs on the native `<dialog>` (docs/specs/web-ui.md#keyboard-and-accessibility):
 * the browser keeps the focus inside while one is open and Escape closes it; on close the dialog
 * leaves the page and the focus returns to the control that opened it. `openSheet` opens one; the
 * two questions the page asks are built on it: a confirmation, and a question that asks for names,
 * checks them as they are typed and shows the server's refusal in place, so a refused name can be
 * corrected without starting over.
 *
 * The module is a chunk of its own, fetched the first time a dialog opens, so the page loads less
 * before a file is editable (NFR-12).
 */

import { command, h } from "./dom.ts";
import { messageOf } from "./states.ts";

export interface Sheet {
  readonly dialog: HTMLDialogElement;
  /** Where the caller puts the content. */
  readonly body: HTMLElement;
  close(): void;
  /** Resolves once the dialog closed, however it closed. */
  readonly closed: Promise<void>;
}

export interface Confirmation {
  readonly title: string;
  readonly message: string;
  /** The button that does it, such as `Delete`. */
  readonly action: string;
  /** Whether it loses work; the button then shows in the fail colour. */
  readonly destructive: boolean;
  /** The `cstudy` command it matches, named beside it. */
  readonly command?: string;
  /** The button that answers no; `Cancel` unless the action is itself a cancel. */
  readonly dismiss?: string;
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

let dialogs = 0;

/** A dialog with a title and a close button; `wide` for a reading pane such as a solution. */
export function openSheet(title: string, wide = false): Sheet {
  const titleId = `dialog-title-${++dialogs}`;
  const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  const close = h("button", { type: "button", class: "ghost sheet-close", "aria-label": "Close" }, "esc ×");
  const body = h("div", { class: "sheet-body" });
  const dialog = h(
    "dialog",
    { class: wide ? "sheet sheet-wide" : "sheet", "aria-labelledby": titleId },
    h("header", { class: "sheet-head" }, h("h2", { id: titleId }, title), close),
    body,
  );
  const closed = new Promise<void>((resolve) => {
    dialog.addEventListener("close", () => {
      dialog.remove();
      opener?.focus({ preventScroll: true });
      resolve();
    });
  });
  close.addEventListener("click", () => dialog.close());
  document.body.append(dialog);
  dialog.showModal();
  return { dialog, body, close: () => dialog.close(), closed };
}

/** Asks `confirmation.message` with Cancel and its action; resolves true for the action. Cancel
 * holds the focus, so Enter never confirms by accident. */
export function confirmAction(confirmation: Confirmation): Promise<boolean> {
  const sheet = openSheet(confirmation.title);
  let answer = false;
  const cancel = h("button", { type: "button", class: "button" }, confirmation.dismiss ?? "Cancel");
  const confirm = h("button", { type: "button", class: `button ${confirmation.destructive ? "danger" : "primary"}` }, confirmation.action);
  cancel.addEventListener("click", () => sheet.close());
  confirm.addEventListener("click", () => {
    answer = true;
    sheet.close();
  });
  const shown = confirmation.command ? [h("p", { class: "sheet-command quiet" }, "as ", command(confirmation.command))] : [];
  sheet.body.append(h("p", { class: "question" }, confirmation.message), ...shown, h("div", { class: "sheet-actions" }, cancel, confirm));
  cancel.focus();
  return sheet.closed.then(() => answer);
}

/** Resolves true once `request.submit` succeeds, false when the dialog is dismissed. */
export function askNames(request: NameRequest): Promise<boolean> {
  const sheet = openSheet(request.title);
  const issue = h("p", { class: "dialog-issue", id: `dialog-issue-${dialogs}`, "aria-live": "polite" });
  const inputs = request.fields.map((field, index) =>
    h("input", {
      id: `dialog-name-${dialogs}-${index}`,
      type: "text",
      value: field.value,
      spellcheck: "false",
      autocomplete: "off",
      autocapitalize: "off",
      "aria-describedby": issue.id,
    }),
  );
  const submit = h("button", { type: "submit", class: "button primary" }, request.action);
  const cancel = h("button", { type: "button", class: "button" }, "Cancel");
  const form = h(
    "form",
    { novalidate: true },
    request.note ? h("p", { class: "quiet" }, request.note) : null,
    ...request.fields.map((field, index) =>
      h(
        "div",
        { class: "field" },
        h("label", { for: inputs[index]?.id ?? "" }, field.label),
        h("span", { class: "dialog-input" }, field.prefix ? h("span", { class: "dialog-prefix", "aria-hidden": "true" }, field.prefix) : null, inputs[index]),
      ),
    ),
    issue,
    h("div", { class: "sheet-actions" }, cancel, submit),
  );
  sheet.body.append(form);
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
  cancel.addEventListener("click", () => sheet.close());
  let done = false;
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    typed = true;
    if (check() !== null) return;
    submit.disabled = true;
    sheet.dialog.setAttribute("aria-busy", "true");
    void request
      .submit(values())
      .catch((error: unknown) => messageOf(error))
      .then((refusal) => {
        sheet.dialog.removeAttribute("aria-busy");
        if (refusal === null) {
          done = true;
          sheet.close();
          return;
        }
        issue.textContent = refusal;
        submit.disabled = false;
        inputs[0]?.focus();
      });
  });
  return sheet.closed.then(() => done);
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
