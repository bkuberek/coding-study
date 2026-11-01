/**
 * The Done dialog (docs/specs/web-ui.md#attempt-view): a rating, or giving up, and notes; then
 * the lines `cstudy done` prints. It is a chunk of its own, fetched when Done is first used
 * (NFR-12).
 */

import "./doneDialog.css";

import { doneCommand, doneLines, type DoneChoice, refreshAttemptsMenu } from "./attempts.ts";
import type { PageContext } from "./context.ts";
import { openSheet } from "./dialogs.ts";
import { command, h } from "./dom.ts";
import { secondsSince } from "./format.ts";
import { problemHash } from "./routes.ts";
import { failure } from "./states.ts";
import type { AttemptStatus, DoneDocument } from "./types.ts";

const RATINGS = ["easy", "ok", "hard"] as const;
const GAVE_UP = "gave-up";
const ITEM = "item";

/** The Done dialog: a rating, or giving up, and notes; then the lines `cstudy done` prints. */
export function openDoneDialog(context: PageContext, status: AttemptStatus): void {
  const sheet = openSheet(`done · ${status.slug}`);
  const isItem = status.kind === ITEM;
  const choices = [...RATINGS, ...(isItem ? [] : [GAVE_UP])];
  const radios = choices.map((value, index) => {
    const input = h("input", { type: "radio", name: "outcome", id: `done-${value}`, value, checked: index === 1 });
    return h("label", { class: `outcome outcome-${value}`, for: `done-${value}` }, input, h("span", {}, value === GAVE_UP ? "gave up" : value));
  });
  const notes = h("textarea", { id: "done-notes", name: "notes", rows: 3, placeholder: "kept on the attempt" });
  const line = h("code", { class: "cmd" });
  const problemArea = h("div", { class: "sheet-error" });
  const submit = h("button", { type: "submit", class: "button primary" }, "Finish");
  const choice = (): DoneChoice => {
    const picked = radios.map((label) => label.querySelector("input")).find((input) => input?.checked)?.value ?? "ok";
    return { rating: picked === GAVE_UP ? null : picked, gaveUp: picked === GAVE_UP, notes: notes.value };
  };
  const update = () => {
    line.textContent = doneCommand(status.slug, choice());
  };
  const form = h(
    "form",
    { class: "sheet-form" },
    h("fieldset", { class: "outcomes" }, h("legend", {}, isItem ? "how it went" : "how it went, or give up"), ...radios),
    h("ul", { class: "plain caps" }, ...capNotes(status).map((note) => h("li", { class: "tone-warn" }, note))),
    h("p", { class: "quiet" }, isItem ? "an item takes a rating only, graded by it alone" : "a rating needs the latest run to pass every case; giving up grades again"),
    h("div", { class: "field" }, h("label", { for: "done-notes" }, "notes"), notes),
    h("p", { class: "sheet-command" }, line),
    problemArea,
    h("div", { class: "sheet-actions" }, h("button", { type: "button", class: "button", "data-close": true }, "Cancel"), submit),
  );
  form.addEventListener("input", update);
  form.querySelector("[data-close]")?.addEventListener("click", () => sheet.close());
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submit.disabled = true;
    problemArea.replaceChildren();
    const picked = choice();
    const body = picked.gaveUp ? { gave_up: true } : { rating: picked.rating };
    context.api
      .post<DoneDocument>(`/api/v1/attempts/${status.attempt_id}/done`, { ...body, notes: picked.notes.trim() || null })
      .then((done) => {
        showOutcome(context, sheet.body, done, status);
        refreshAttemptsMenu(context);
        void context.mock.refresh();
      })
      .catch((error: unknown) => {
        problemArea.replaceChildren(failure(error));
        submit.disabled = false;
      });
  });
  update();
  sheet.body.append(form);
  radios[1]?.querySelector("input")?.focus();
}

/** Why the grade may land below the rating, as the attempt stands. */
function capNotes(status: AttemptStatus): string[] {
  const notes: string[] = [];
  if (status.solution_revealed && status.kind !== ITEM) notes.push("the solution was revealed: the attempt is graded as again");
  if (status.hints.used > 0 && status.kind !== ITEM) notes.push("a hint was used: the grade is capped at ok");
  const limit = status.timer?.limit_s ?? null;
  if (limit !== null && status.kind !== ITEM && secondsSince(status.started_at, Date.now()) > limit) {
    notes.push("past the time box: the grade is capped at hard");
  }
  return notes;
}

function showOutcome(context: PageContext, body: HTMLElement, done: DoneDocument, status: AttemptStatus): void {
  const [summary, review] = doneLines(done, status.levels?.last ?? null);
  const open = h("a", { href: problemHash(done.slug), class: "button primary" }, `Open ${done.slug}`);
  body.replaceChildren(
    h("p", { class: "eyebrow" }, "finished"),
    h("pre", { class: "outcome-lines" }, h("strong", {}, summary), "\n", review),
    h("p", { class: "quiet" }, "as ", command(`cstudy done ${done.slug}`), " prints it"),
    h("div", { class: "sheet-actions" }, h("a", { href: "#/", class: "button" }, "Problems"), open),
  );
  for (const link of body.querySelectorAll("a")) link.addEventListener("click", () => body.closest("dialog")?.close());
  context.shell.announce(summary);
  open.focus();
}
