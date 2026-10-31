/**
 * Modal dialogs on the native `<dialog>` (docs/specs/web-ui.md#keyboard-and-accessibility): the
 * browser keeps the focus inside while it is open and Escape closes it; on close the dialog
 * leaves the page and the focus returns to the control that opened it.
 */

import { h } from "./dom.ts";

export interface Sheet {
  readonly dialog: HTMLDialogElement;
  /** Where the caller puts the content. */
  readonly body: HTMLElement;
  close(): void;
  /** Resolves once the dialog closed, however it closed. */
  readonly closed: Promise<void>;
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

/** Asks `question` with Cancel and `confirmLabel`; resolves true for `confirmLabel`. Cancel
 * holds the focus, so Enter never confirms by accident. */
export function confirmDialog(question: string, confirmLabel: string): Promise<boolean> {
  const sheet = openSheet("confirm");
  let answer = false;
  const cancel = h("button", { type: "button", class: "button" }, "Cancel");
  const confirm = h("button", { type: "button", class: "button primary" }, confirmLabel);
  cancel.addEventListener("click", () => sheet.close());
  confirm.addEventListener("click", () => {
    answer = true;
    sheet.close();
  });
  sheet.body.append(h("p", { class: "question" }, question), h("div", { class: "sheet-actions" }, cancel, confirm));
  cancel.focus();
  return sheet.closed.then(() => answer);
}
