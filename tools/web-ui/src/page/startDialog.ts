/**
 * The Start dialog (docs/specs/web-ui.md#problem-view): the language, a fresh start and the time
 * box of `cstudy start`, which it names as it runs. It is a chunk of its own, fetched when the
 * first Start control is used (NFR-12).
 */

import { defaultLanguage, refreshAttemptsMenu, startBody, startLine, type StartChoice } from "./attempts.ts";
import type { PageContext } from "./context.ts";
import { openSheet } from "./dialogs.ts";
import { h } from "./dom.ts";
import { attemptHash } from "./routes.ts";
import { failure } from "./states.ts";
import type { AttemptStatus, ProblemDocument } from "./types.ts";

const PROJECT = "project";
const TIMER_RANGE = { min: 1, max: 600 } as const;

/** The Start dialog of a problem; `scheduled` problems start a review attempt. */
export function openStartDialog(context: PageContext, problem: ProblemDocument, scheduled: boolean): void {
  const sheet = openSheet(`start · ${problem.slug}`);
  const fixedLanguage = problem.kind === PROJECT ? (problem.languages[0] ?? null) : null;
  const choosesLanguage = problem.kind !== PROJECT && problem.languages.length > 0;
  const language = h(
    "select",
    { id: "start-language", name: "language" },
    ...problem.languages.map((name) => h("option", { value: name, selected: name === defaultLanguage(problem, context.session.default_lang) }, name)),
  );
  const fresh = h("input", { type: "checkbox", id: "start-fresh", name: "fresh" });
  const minutes = h("input", { type: "number", id: "start-timer", name: "timer", min: TIMER_RANGE.min, max: TIMER_RANGE.max, step: 1, placeholder: "none", inputmode: "numeric" });
  const line = h("code", { class: "cmd" });
  const resumeNote = h("p", { class: "quiet", role: "status" });
  const submit = h("button", { type: "submit", class: "button primary" }, "Start");
  const problemArea = h("div", { class: "sheet-error" });
  const choice = (): StartChoice => ({
    slug: problem.slug,
    language: choosesLanguage ? language.value : null,
    fresh: fresh.checked,
    minutes: minutes.value,
  });
  const update = () => {
    const current = choice();
    line.textContent = startLine(current);
    const open = problem.in_progress.find((attempt) => current.language === null || attempt.language === current.language);
    const resumes = open !== undefined && !current.fresh;
    submit.textContent = resumes ? "Resume" : "Start";
    resumeNote.textContent = open === undefined ? "" : current.fresh ? `attempt ${open.attempt_id} is in progress: Start fresh replaces it` : `attempt ${open.attempt_id} is in progress: Resume reopens it`;
  };
  const form = h(
    "form",
    { class: "sheet-form" },
    choosesLanguage
      ? h("div", { class: "field" }, h("label", { for: "start-language" }, "language"), language)
      : h("p", { class: "field quiet" }, fixedLanguage ? `${fixedLanguage}: a project starts in its one language` : "notes: an item takes no language"),
    h("div", { class: "field check" }, fresh, h("label", { for: "start-fresh" }, "start fresh"), h("p", { class: "quiet" }, "archive your current files to .archive/ and begin again")),
    h(
      "div",
      { class: "field" },
      h("label", { for: "start-timer" }, "time box, minutes"),
      minutes,
      h("p", { class: "quiet" }, "empty for none; finishing past the box caps the grade at hard"),
    ),
    scheduled ? h("p", { class: "review-note tone-info" }, "review attempt: your current files move to .archive/") : null,
    resumeNote,
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
    context.api
      .post<AttemptStatus>("/api/v1/attempts", startBody(choice()))
      .then((status) => {
        refreshAttemptsMenu(context);
        void context.mock.refresh();
        sheet.close();
        location.hash = attemptHash(status.attempt_id);
      })
      .catch((error: unknown) => {
        problemArea.replaceChildren(failure(error));
        submit.disabled = false;
      });
  });
  update();
  sheet.body.append(form);
  (choosesLanguage ? language : fresh).focus();
}
