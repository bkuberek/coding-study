/**
 * The attempt flows (docs/specs/web-ui.md#problem-view, docs/specs/web-ui.md#attempt-view): the
 * Start dialog, the Hint button with the hints this tab revealed, and the Done dialog with the
 * outcome lines `cstudy done` prints. Each control names the command it runs, and every refusal
 * shows the CLI's message.
 */

import { quoted, startCommand } from "./commands.ts";
import type { PageContext } from "./context.ts";
import { openSheet } from "./dialogs.ts";
import { command, h, rendered } from "./dom.ts";
import { secondsSince, solveTime } from "./format.ts";
import { attemptHash, problemHash } from "./routes.ts";
import { solutionButton } from "./solution.ts";
import { failure } from "./states.ts";
import type { AttemptStatus, DoneDocument, HintResult, ProblemDocument, ProblemList } from "./types.ts";

const RATINGS = ["easy", "ok", "hard"] as const;
const GAVE_UP = "gave-up";
const PROJECT = "project";
const ITEM = "item";
const LEVELS_CAP = "levels";
const HINT_COMMAND = "cstudy hint";
const TIMER_RANGE = { min: 1, max: 600 } as const;

export interface StartChoice {
  readonly slug: string;
  /** Null for a project, which starts in its one language, and for an item. */
  readonly language: string | null;
  readonly fresh: boolean;
  /** The time box field as typed: minutes, or empty for none. */
  readonly minutes: string;
}

export interface DoneChoice {
  /** Null with `gaveUp`. */
  readonly rating: string | null;
  readonly gaveUp: boolean;
  readonly notes: string;
}

/** The language `cstudy start` gets `--lang` for: none for a project or an item, else
 * `default_lang` when the problem has it, else its first language. */
export function defaultLanguage(problem: Pick<ProblemDocument, "kind" | "languages">, defaultLang: string): string | null {
  if (problem.kind === PROJECT || problem.languages.length === 0) return null;
  return problem.languages.includes(defaultLang) ? defaultLang : (problem.languages[0] ?? null);
}

/** `POST /api/v1/attempts`; a time box that is not a whole number goes as typed, for the
 * server's refusal. */
export function startBody(choice: StartChoice): {
  slug: string;
  language: string | null;
  fresh: boolean;
  timer_minutes: number | string | null;
} {
  const minutes = choice.minutes.trim();
  const timer = minutes === "" ? null : Number.isInteger(Number(minutes)) ? Number(minutes) : minutes;
  return { slug: choice.slug, language: choice.language, fresh: choice.fresh, timer_minutes: timer };
}

/** The `cstudy start` the dialog runs; the page never opens an editor. */
export function startLine(choice: StartChoice): string {
  const minutes = choice.minutes.trim();
  const flags = [choice.fresh ? "--fresh" : null, minutes ? `--timer ${minutes}m` : null, "--no-open"];
  return [startCommand(choice.slug, choice.language), ...flags].filter(Boolean).join(" ");
}

/** How `cstudy hint` heads a hint, or what it prints instead of one. */
export function hintText(result: HintResult): string {
  if ("hint" in result) return `hint ${result.hint.number} of ${result.hint.total}`;
  if ("locked_until_level" in result) return `no more hints until level ${result.locked_until_level} opens`;
  return "no more hints";
}

export function doneCommand(slug: string, choice: DoneChoice): string {
  const finish = choice.gaveUp ? "--gave-up" : `--rating ${choice.rating ?? ""}`;
  const notes = choice.notes.trim() ? `--notes ${quoted(choice.notes.trim())}` : null;
  return [`cstudy done ${slug}`, finish, notes].filter(Boolean).join(" ");
}

/** The two lines `cstudy done` prints; `levelsLast` is a project's last level. */
export function doneLines(done: DoneDocument, levelsLast: number | null): [string, string] {
  const levels = done.levels_finished === null ? null : `levels ${done.levels_finished} of ${levelsLast ?? "?"}`;
  const parts = [done.slug, done.language, done.status, levels, solveTime(done.solve_s), ratingText(done), `hints ${done.hints_used}`];
  const review = done.next_review;
  const when = review.in_days === 1 ? "in 1 day" : `in ${review.in_days} days`;
  return [parts.filter(Boolean).join(" · "), `next review  ${review.due_on} (${when}) · ease ${review.ease.toFixed(2)}`];
}

/** `rating ok`; a project grade its levels capped below the rating says so, as `cstudy done` does. */
function ratingText(done: DoneDocument): string {
  if (done.rating === null) return "gave up";
  const rating = `rating ${done.rating}`;
  return done.caps.includes(LEVELS_CAP) ? `${rating}, capped at ${done.grade}` : rating;
}

/** Refreshes the top bar's menu of attempts in progress after a start or a finish. */
export function refreshAttemptsMenu(context: PageContext): void {
  void context.api
    .get<ProblemList>("/api/v1/problems")
    .then((list) => context.shell.setAttempts(list.entries))
    .catch(() => {});
}

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

/** The Hint button for the attempt's header, and the hints this tab revealed, for its
 * statement pane. The button is disabled with the lock message while a mock interview runs. */
class HintControl {
  readonly button: HTMLButtonElement;
  readonly panel: HTMLElement;
  readonly #context: PageContext;
  readonly #status: AttemptStatus;
  readonly #count: HTMLElement;
  readonly #revealed: HTMLElement;
  readonly #notice: HTMLElement;
  #used: number;
  /** The level a project's next hint opens with, while it is locked. */
  #lockedUntil: number | null;
  #lock: string | null = null;

  constructor(context: PageContext, status: AttemptStatus) {
    this.#context = context;
    this.#status = status;
    this.#used = status.hints.used;
    this.#lockedUntil = status.hints.locked_until_level;
    this.button = h("button", { type: "button", class: "button" }, "Hint");
    this.#count = h("span");
    this.#revealed = h("div", { class: "hints-revealed" });
    this.#notice = h("p", { class: "hint-notice", role: "status" });
    this.panel = h(
      "section",
      { class: "hints", "aria-label": "Hints" },
      h("p", {}, this.#count, h("span", { class: "quiet" }, " · any hint caps the review grade at ok")),
      this.#notice,
      this.#revealed,
    );
    this.button.addEventListener("click", () => void this.reveal());
    this.button.hidden = status.hints.total === 0;
    this.panel.hidden = status.hints.total === 0;
    this.#render();
  }

  /** `message` disables the button and describes why; null enables it. */
  setLock(message: string | null): void {
    this.#lock = message;
    this.#render();
  }

  async reveal(): Promise<void> {
    if (this.#lock !== null) return;
    this.button.disabled = true;
    this.#notice.textContent = "";
    try {
      const result = await this.#context.api.post<HintResult>(`/api/v1/attempts/${this.#status.attempt_id}/hints`, {});
      const text = hintText(result);
      if ("hint" in result) {
        this.#used = result.hint.number;
        this.#lockedUntil = null;
        const hint = h("article", { class: "hint" }, h("h3", { class: "eyebrow" }, text), rendered(result.hint.html, "prose prose-compact"));
        this.#revealed.prepend(hint);
        // The hints sit under the statement; bring the new one into view without moving the focus.
        hint.scrollIntoView({ block: "nearest" });
      } else {
        this.#lockedUntil = "locked_until_level" in result ? result.locked_until_level : null;
        this.#notice.textContent = text;
      }
      this.#context.shell.announce(text);
    } catch (error) {
      this.#notice.replaceChildren(failure(error));
    } finally {
      this.#render();
    }
  }

  #render(): void {
    const { slug, hints } = this.#status;
    const next = this.#lockedUntil === null ? "" : `, the next opens with level ${this.#lockedUntil}`;
    this.#count.textContent = `hints ${this.#used} of ${hints.total}${next}`;
    this.button.disabled = this.#lock !== null;
    this.button.title = this.#lock ?? `${HINT_COMMAND} ${slug}: reveal the next hint; any hint caps the review grade at ok`;
    if (this.#lock === null) this.button.removeAttribute("aria-description");
    else this.button.setAttribute("aria-description", this.#lock);
  }
}

export interface AttemptFlows {
  /** Hint, Solution and Done, for the attempt's header. */
  readonly actions: HTMLElement;
  /** The hints this tab revealed, for the statement pane. */
  readonly hints: HTMLElement;
}

/** The attempt's Hint, Solution and Done controls; Hint and Solution follow the mock lock. */
export function attemptFlows(context: PageContext, status: AttemptStatus): AttemptFlows {
  const hints = new HintControl(context, status);
  context.mock.follow(HINT_COMMAND, hints.button, (lock) => hints.setLock(lock));
  const done = h("button", { type: "button", class: "button", title: `cstudy done ${status.slug}: finish and schedule the review` }, "Done…");
  done.addEventListener("click", () => openDoneDialog(context, status));
  const actions = h("span", { class: "flow-actions", role: "group", "aria-label": "Attempt" }, hints.button, solutionButton(context, status.slug), done);
  return { actions, hints: hints.panel };
}

/** The Done dialog: a rating, or giving up, and notes; then the lines `cstudy done` prints. */
function openDoneDialog(context: PageContext, status: AttemptStatus): void {
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
