/**
 * The attempt flows (docs/specs/web-ui.md#problem-view, docs/specs/web-ui.md#attempt-view): what
 * the Start and Done dialogs say and send, the Hint button with the hints this tab revealed, and
 * the controls of the attempt's header. The dialogs are chunks of their own (`startDialog.ts`,
 * `doneDialog.ts`), fetched when first used. Each control names the command it runs, and every
 * refusal shows the CLI's message.
 */

import { quoted, startCommand } from "./commands.ts";
import type { PageContext } from "./context.ts";
import { h, rendered } from "./dom.ts";
import { solveTime } from "./format.ts";
import { openLazily } from "./lazy.ts";
import { solutionButton } from "./solution.ts";
import { failure } from "./states.ts";
import type { AttemptStatus, DoneDocument, HintResult, ProblemDocument, ProblemList } from "./types.ts";

const PROJECT = "project";
const LEVELS_CAP = "levels";
const HINT_COMMAND = "cstudy hint";

/** What a review attempt does to the files of the attempt before it: it archives them, which
 * deletes nothing, and the Problem view's History reads them from there. */
const ARCHIVE_NOTE = "your current files move to .archive/ — nothing is deleted, and History keeps them readable";
/** The Start dialog's note of a problem with a review due. */
export const REVIEW_DIALOG_NOTE = `review attempt: ${ARCHIVE_NOTE}`;
/** The Practise panel's line of a problem with a review due. */
export const REVIEW_PRACTISE_NOTE = `a start is a review attempt: ${ARCHIVE_NOTE}`;

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
 * `default_lang` when the problem has it, else its first language. A language in `blocked`, such as
 * a Java the selected JDK cannot run, gives way to the first one that is not; when every language
 * is blocked, the usual choice stays. */
export function defaultLanguage(
  problem: Pick<ProblemDocument, "kind" | "languages">,
  defaultLang: string,
  blocked: ReadonlySet<string> = new Set(),
): string | null {
  if (problem.kind === PROJECT || problem.languages.length === 0) return null;
  const usual = problem.languages.includes(defaultLang) ? defaultLang : (problem.languages[0] ?? null);
  if (usual === null || !blocked.has(usual)) return usual;
  return problem.languages.find((language) => !blocked.has(language)) ?? usual;
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

  /** Takes the count and the lock of the status read after a level opened. */
  update(status: AttemptStatus): void {
    this.#used = status.hints.used;
    this.#lockedUntil = status.hints.locked_until_level;
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
  /** Takes the status read after a level opened; the hints already revealed stay. */
  update(status: AttemptStatus): void;
}

/** The attempt's Hint, Solution and Done controls; Hint and Solution follow the mock lock. */
export function attemptFlows(context: PageContext, status: AttemptStatus): AttemptFlows {
  const hints = new HintControl(context, status);
  context.mock.follow(HINT_COMMAND, hints.button, (lock) => hints.setLock(lock));
  const done = h("button", { type: "button", class: "button", title: `cstudy done ${status.slug}: finish and schedule the review` }, "Done…");
  done.addEventListener("click", () => openLazily(context, () => import("./sheets.ts"), (dialog) => dialog.openDoneDialog(context, status)));
  const actions = h("span", { class: "flow-actions", role: "group", "aria-label": "Attempt" }, hints.button, solutionButton(context, status.slug), done);
  return { actions, hints: hints.panel, update: (status) => hints.update(status) };
}
