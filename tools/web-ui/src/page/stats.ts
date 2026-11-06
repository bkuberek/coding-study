/**
 * The Progress view (docs/specs/web-ui.md#progress-view): `cstudy stats` with its `by` and
 * `since`, the reviews due and ahead, the export download, and `cstudy import` of a chosen file
 * after its confirmation.
 */

import "./stats.css";

import { confirmed } from "./confirmation.ts";
import type { Cleanup, PageContext } from "./context.ts";
import { confirmAction } from "./dialogs.ts";
import { command, h } from "./dom.ts";
import { solveTime } from "./format.ts";
import { problemHash } from "./routes.ts";
import { openStartDialog } from "./startDialog.ts";
import { empty, failure, loading, showFailure } from "./states.ts";
import type { ListEntry, ProblemDocument, ProblemList, StatsDocument, StatsGroup } from "./types.ts";

const GROUPINGS = ["pattern", "track", "lang", "difficulty"] as const;
const DEFAULT_GROUPING = "pattern";
const COLUMNS = ["group", "problems", "attempted", "passed", "mastered", "pass rate", "solve time", "weakness"] as const;
const NO_VALUE = "-";
const PERCENT = 100;
const REVIEW_DAYS = 14;
const DAY_MS = 86_400_000;

export interface ReviewsAhead {
  /** Due today or overdue, oldest first. */
  readonly due: readonly ListEntry[];
  /** Due within the next 14 days, soonest first. */
  readonly upcoming: readonly ListEntry[];
}

/** A row of the `cstudy stats` table: pass rate rounded half up, as the command rounds it. */
export function groupCells(group: StatsGroup): string[] {
  const rate = group.pass_rate === null ? NO_VALUE : `${Math.floor(group.pass_rate * PERCENT + 0.5)}%`;
  const solve = group.median_solve_s === null ? NO_VALUE : solveTime(group.median_solve_s);
  const counts = [group.problems, group.attempted, group.passed, group.mastered].map(String);
  return [group.group, ...counts, rate, solve, group.weakness.toFixed(2)];
}

/** The labelled lines under the `cstudy stats` table. */
export function summaryLines(stats: StatsDocument): [string, string][] {
  const { attempts, reviews, bench } = stats;
  const finished = `${attempts.finished} finished${stats.since ? ` since ${stats.since}` : ""}`;
  const streak = `streak ${attempts.streak_days} ${attempts.streak_days === 1 ? "day" : "days"}`;
  const benched = Object.values(bench).reduce((total, count) => total + count, 0);
  const verdicts = Object.entries(bench).map(([verdict, count]) => `${count} ${verdict}`);
  return [
    ["attempts", [finished, `${attempts.last_7_days} in the last 7 days`, streak].join(" · ")],
    ["reviews", `${reviews.due_today} due today · ${reviews.overdue} overdue`],
    ["bench", [`${benched} benched`, ...verdicts].join(" · ")],
  ];
}

export function reviewsAhead(entries: readonly ListEntry[], today: string): ReviewsAhead {
  const byDue = (a: ListEntry, b: ListEntry) => (a.due_on ?? "").localeCompare(b.due_on ?? "");
  const horizon = new Date(Date.parse(today) + REVIEW_DAYS * DAY_MS).toISOString().slice(0, 10);
  const isDue = (entry: ListEntry) => entry.due_on !== null && entry.due_on <= today;
  const due = entries.filter(isDue).sort(byDue);
  const upcoming = entries.filter((entry) => entry.due_on !== null && entry.due_on > today && entry.due_on <= horizon).sort(byDue);
  return { due, upcoming };
}

/** `attempts 6 · test_runs 4`, as `cstudy import` counts the rows. */
export function importedText(counts: Readonly<Record<string, number>>): string {
  return Object.entries(counts)
    .map(([table, count]) => `${table} ${count}`)
    .join(" · ");
}

export function statsCommand(by: string, since: string): string {
  const flags = [by === DEFAULT_GROUPING ? null : `--by ${by}`, since ? `--since ${since}` : null];
  return ["cstudy stats", ...flags].filter(Boolean).join(" ");
}

export function progressView(context: PageContext): Cleanup {
  const { shell } = context;
  shell.setView("progress");
  shell.setCommand("cstudy stats");
  shell.setStatus({ mode: "PROGRESS", where: "progress.db" });
  shell.main.replaceChildren(
    h(
      "section",
      { class: "progress", "aria-labelledby": "progress-heading" },
      h("header", { class: "view-head" }, h("h1", { id: "progress-heading" }, "progress")),
      h("div", { class: "progress-grid" }, statistics(context), h("div", { class: "progress-side" }, reviews(context), backup(context))),
    ),
  );
  return () => {};
}

function statistics(context: PageContext): HTMLElement {
  const by = h("select", { id: "stats-by" }, ...GROUPINGS.map((name) => h("option", { value: name }, name)));
  const since = h("input", { type: "date", id: "stats-since" });
  const region = h("div", { class: "stats-region" }, loading());
  let request = 0;
  const load = () => {
    const current = ++request;
    context.shell.setCommand(statsCommand(by.value, since.value));
    const query = new URLSearchParams({ by: by.value });
    if (since.value) query.set("since", since.value);
    region.setAttribute("aria-busy", "true");
    context.api
      .get<StatsDocument>(`/api/v1/stats?${query}`)
      .then((stats) => {
        if (current === request) region.replaceChildren(statsTable(stats), summary(stats));
      })
      .catch((error: unknown) => showFailure(region, error))
      .finally(() => region.removeAttribute("aria-busy"));
  };
  by.addEventListener("change", load);
  since.addEventListener("change", load);
  load();
  return h(
    "section",
    { class: "side-block stats", "aria-labelledby": "stats-heading" },
    h("h2", { id: "stats-heading", class: "eyebrow" }, "statistics"),
    h(
      "div",
      { class: "stats-controls" },
      h("div", { class: "field" }, h("label", { for: "stats-by" }, "by"), by),
      h("div", { class: "field" }, h("label", { for: "stats-since" }, "since"), since),
    ),
    region,
  );
}

function statsTable(stats: StatsDocument): HTMLElement {
  if (stats.groups.length === 0) return empty("no groups with ready content");
  // Focusable, so the keyboard scrolls the table where it is wider than the window.
  return h("div", { class: "table-scroll", role: "region", tabindex: "0", "aria-label": "Statistics by group" }, groupTable(stats));
}

function groupTable(stats: StatsDocument): HTMLElement {
  return h(
    "table",
    { class: "stats-table" },
    h("caption", { class: "sr-only" }, `cstudy stats by ${stats.by}`),
    h("thead", {}, h("tr", {}, ...COLUMNS.map((column, index) => h("th", { scope: "col", class: index ? "num" : null }, column)))),
    h(
      "tbody",
      {},
      ...stats.groups.map((group) =>
        h("tr", {}, ...groupCells(group).map((cell, index) => (index ? h("td", { class: "num" }, cell) : h("th", { scope: "row" }, cell)))),
      ),
    ),
  );
}

function summary(stats: StatsDocument): HTMLElement {
  return h("dl", { class: "stats-summary" }, ...summaryLines(stats).flatMap(([label, value]) => [h("dt", {}, label), h("dd", {}, value)]));
}

function reviews(context: PageContext): HTMLElement {
  const region = h("div", {}, loading());
  context.api
    .get<ProblemList>("/api/v1/problems")
    .then((list) => {
      const ahead = reviewsAhead(list.entries, list.today);
      region.replaceChildren(
        h("h3", { class: "eyebrow" }, "due today and overdue"),
        ahead.due.length ? reviewList(context, ahead.due) : h("p", { class: "quiet" }, "nothing due"),
        h("h3", { class: "eyebrow" }, `the next ${REVIEW_DAYS} days`),
        ahead.upcoming.length ? reviewList(context, ahead.upcoming) : h("p", { class: "quiet" }, "nothing scheduled"),
      );
    })
    .catch((error: unknown) => showFailure(region, error));
  return h("section", { class: "side-block reviews", "aria-labelledby": "reviews-heading" }, h("h2", { id: "reviews-heading", class: "eyebrow" }, "reviews"), region);
}

function reviewList(context: PageContext, entries: readonly ListEntry[]): HTMLElement {
  return h(
    "ul",
    { class: "plain review-list" },
    ...entries.map((entry) => {
      const start = h("button", { type: "button", class: "button", title: `cstudy start ${entry.slug}` }, "Start");
      start.addEventListener("click", () => {
        start.disabled = true;
        context.api
          .get<ProblemDocument>(`/api/v1/problems/${encodeURIComponent(entry.slug)}`)
          .then((problem) => openStartDialog(context, problem, true))
          .catch((error: unknown) => start.replaceWith(failure(error)))
          .finally(() => {
            start.disabled = false;
          });
      });
      return h("li", {}, h("span", { class: "num" }, entry.due_on ?? ""), " ", h("a", { href: problemHash(entry.slug) }, entry.slug), " ", start);
    }),
  );
}

function backup(context: PageContext): HTMLElement {
  const file = h("input", { type: "file", id: "import-file", accept: "application/json,.json" });
  const submit = h("button", { type: "submit", class: "button" }, "Import");
  const outcome = h("div", { role: "status" });
  const form = h(
    "form",
    { class: "import-form" },
    h("label", { for: "import-file" }, "a cstudy export"),
    file,
    submit,
  );
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const chosen = file.files?.[0];
    if (!chosen) {
      outcome.replaceChildren(h("p", { class: "quiet" }, "choose an export file first"));
      return;
    }
    submit.disabled = true;
    void importFile(context, chosen)
      .then((counts) => outcome.replaceChildren(h("p", {}, counts === null ? "not imported" : `imported  ${importedText(counts)}`)))
      .catch((error: unknown) => outcome.replaceChildren(failure(error)))
      .finally(() => {
        submit.disabled = false;
      });
  });
  return h(
    "section",
    { class: "side-block backup", "aria-labelledby": "backup-heading" },
    h("h2", { id: "backup-heading", class: "eyebrow" }, "backup"),
    h("p", {}, h("a", { href: "/api/v1/progress/export", download: "progress-export.json", class: "button" }, "Download progress-export.json")),
    h("p", { class: "quiet" }, "as ", command("cstudy export"), " writes it; nothing is written in the workspace"),
    form,
    h("p", { class: "quiet" }, "as ", command("cstudy import"), ", into a progress.db that holds no progress yet"),
    outcome,
  );
}

/** `cstudy import` of `file` after the server's question; null when declined. */
async function importFile(context: PageContext, file: File): Promise<Record<string, number> | null> {
  let document: unknown;
  try {
    document = JSON.parse(await file.text());
  } catch {
    throw new Error(`${file.name} is not JSON`);
  }
  const send = (confirm: boolean) => context.api.post<{ imported: Record<string, number> }>("/api/v1/progress/import", { confirm, export: document });
  const answer = await confirmed(send, (message) => confirmAction({ title: "confirm", message, action: "Import", destructive: false }));
  return answer?.imported ?? null;
}
