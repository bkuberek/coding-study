/**
 * The Problem view (docs/specs/web-ui.md#problem-view): the header, the `cstudy show` statement,
 * how to start or resume it, its approaches, and its `cstudy history`, each attempt that is over
 * with a way to read its code (`pastFiles.ts`).
 */

import "./problem.css";

import { defaultLanguage, REVIEW_PRACTISE_NOTE } from "../attempts.ts";
import { startCommand } from "../commands.ts";
import type { Cleanup, PageContext } from "../context.ts";
import { solutionButton } from "../solution.ts";
import { badge, command, h, rendered } from "../dom.ts";
import { localMinute, problemBadge, solveTime } from "../format.ts";
import { openLazily } from "../lazy.ts";
import { bestLine, goalLines, pastStatus } from "../levels.ts";
import { needsList, readNeeds } from "../needs.ts";
import { attemptHash, guideHash, setHash } from "../routes.ts";
import { setControl, setsHolding } from "../setControl.ts";
import { empty, failure, loading, showFailure } from "../states.ts";
import type { History, PastAttempt, ProblemDocument, Rendered, SetList } from "../types.ts";

const IN_PROGRESS = "in_progress";

export function problemView(context: PageContext, slug: string): Cleanup {
  const { api, shell } = context;
  const base = `/api/v1/problems/${encodeURIComponent(slug)}`;
  shell.setView(null);
  shell.setCommand(`cstudy show ${slug}`);
  shell.setStatus({ mode: "PROBLEM", where: slug });
  const page = h("article", { class: "problem", "aria-busy": "true" }, loading());
  shell.main.replaceChildren(page);

  void Promise.all([
    api.get<ProblemDocument>(base),
    api.get<Rendered>(`${base}/statement`),
    api.get<History>(`${base}/history`),
    // A sets.yaml that does not parse stops nothing but the sets.
    api.get<SetList>("/api/v1/sets").catch((error: unknown) => failure(error)),
  ])
    .then(([problem, statement, history, sets]) => {
      page.removeAttribute("aria-busy");
      page.replaceChildren(header(problem), h("div", { class: "problem-grid" }, statementPane(statement), side(context, problem, history, sets)));
      shell.setStatus({ mode: "PROBLEM", where: `${problem.slug} · ${problem.kind} · ${problem.difficulty}` });
      document.title = `${problem.title} · cstudy`;
    })
    .catch((error: unknown) => showFailure(page, error));
  return () => {};
}

function header(problem: ProblemDocument): HTMLElement {
  const status = problemBadge(problem.status, problem.levels);
  const facts = [problem.id ? `#${problem.id}` : null, problem.track, ...problem.patterns, problem.kind].filter(Boolean);
  return h(
    "header",
    { class: "problem-head" },
    h("p", { class: "eyebrow" }, facts.join(" · ")),
    h("h1", {}, problem.title),
    h(
      "p",
      { class: "problem-facts" },
      h("span", { class: `diff diff-${problem.difficulty}` }, problem.difficulty),
      badge(status.glyph, status.text, status.tone),
      problem.due_on ? h("span", { class: "quiet" }, `due ${problem.due_on}`) : null,
      problem.languages.length ? h("span", { class: "quiet" }, problem.languages.join(" · ")) : null,
    ),
  );
}

function statementPane(statement: Rendered): HTMLElement {
  return h("section", { class: "statement-pane", "aria-label": "Statement" }, rendered(statement.html, "prose"));
}

function setsSection(context: PageContext, slug: string, sets: SetList | HTMLElement): HTMLElement {
  const section = h("section", { class: "side-block", "aria-labelledby": "sets-heading" }, h("h2", { id: "sets-heading", class: "eyebrow" }, "sets"));
  if (sets instanceof HTMLElement) {
    section.append(sets);
    return section;
  }
  const links = h("ul", { class: "plain" });
  const show = (names: readonly string[]) => links.replaceChildren(...names.map((name) => h("li", {}, h("a", { href: setHash(name) }, name))));
  const held = setsHolding(sets.sets, slug);
  show(held);
  section.append(links, h("p", {}, setControl(context, slug, { held, closed: show, label: "Add to a set…" })));
  return section;
}

function side(context: PageContext, problem: ProblemDocument, history: History, sets: SetList | HTMLElement): HTMLElement {
  return h(
    "aside",
    { class: "problem-side", "aria-label": "Practice" },
    needsSection(context, problem),
    guidesSection(problem),
    practice(context, problem, history),
    setsSection(context, problem.slug, sets),
    problem.approaches.length ? approaches(problem) : null,
    historySection(context, problem.slug, history),
  );
}

/** The concept guides that teach what the problem practises, each a link to its Guides view; null for none. */
function guidesSection(problem: ProblemDocument): HTMLElement | null {
  if (problem.guides.length === 0) return null;
  return h(
    "section",
    { class: "side-block", "aria-labelledby": "guides-heading" },
    h("h2", { id: "guides-heading", class: "eyebrow" }, "read first"),
    h(
      "ul",
      { class: "plain problem-guides" },
      ...problem.guides.map((guide) => h("li", {}, h("a", { href: guideHash(guide.slug) }, guide.title), guide.read ? h("span", { class: "quiet" }, " · read") : null)),
    ),
  );
}

/** What a service project depends on, each with its state here, read as the view opens; null for any other problem. */
function needsSection(context: PageContext, problem: ProblemDocument): HTMLElement | null {
  if (problem.requires === null) return null;
  const heading = h("h2", { id: "needs-heading", class: "eyebrow" }, "needs");
  const section = h("section", { class: "side-block needs", "aria-labelledby": "needs-heading" }, heading, loading());
  void readNeeds(context, problem.slug).then(
    (rows) => section.replaceChildren(heading, rows === null ? empty("nothing beyond its language") : needsList(rows)),
    (error: unknown) => section.replaceChildren(heading, failure(error)),
  );
  return section;
}

function practice(context: PageContext, problem: ProblemDocument, history: History): HTMLElement {
  const scheduled = history.schedule !== null;
  const language = defaultLanguage(problem, context.session.default_lang);
  const start = h("button", { type: "button", class: "button primary", title: `${startCommand(problem.slug, language)} --no-open` }, "Start…");
  start.addEventListener("click", () => openLazily(context, () => import("../sheets.ts"), (dialog) => dialog.openStartDialog(context, problem, scheduled)));
  const solution = solutionButton(context, problem.slug);
  const resumes = problem.in_progress.map((attempt) =>
    h(
      "li",
      {},
      h(
        "a",
        { href: attemptHash(attempt.attempt_id), class: "button primary" },
        `Resume ${attempt.language ?? "notes"} · attempt ${attempt.attempt_id}`,
      ),
      h("span", { class: "quiet" }, ` ${attempt.mode}`),
    ),
  );
  return h(
    "section",
    { class: "side-block", "aria-labelledby": "practice-heading" },
    h("h2", { id: "practice-heading", class: "eyebrow" }, "practise"),
    resumes.length ? h("ul", { class: "plain" }, ...resumes) : null,
    h("p", { class: "practice-actions" }, start, solution),
    scheduled ? h("p", { class: "quiet" }, REVIEW_PRACTISE_NOTE) : null,
    problem.hints_total ? h("p", { class: "quiet" }, `${problem.hints_total} hints · any hint caps the review grade at ok`) : null,
    problem.levels ? h("p", { class: "quiet" }, `${problem.levels.last} levels, each opened by passing the one before`) : null,
    ...goalLines(history.levels).map((goal) => h("p", { class: "level-goal" }, goal)),
  );
}

function approaches(problem: ProblemDocument): HTMLElement {
  return h(
    "section",
    { class: "side-block", "aria-labelledby": "approaches-heading" },
    h("h2", { id: "approaches-heading", class: "eyebrow" }, "approaches"),
    h(
      "ul",
      { class: "plain approaches" },
      ...problem.approaches.map((approach) =>
        h("li", {}, h("span", { class: `role role-${approach.role}` }, approach.role), approach.name),
      ),
    ),
    problem.bench ? h("p", { class: "quiet" }, "bench: ", command(`cstudy bench ${problem.slug}`)) : null,
  );
}

function historySection(context: PageContext, slug: string, history: History): HTMLElement {
  const schedule = history.schedule;
  const review = schedule
    ? `due ${schedule.due_on} · interval ${schedule.interval_days}d · ease ${schedule.ease.toFixed(2)} · reps ${schedule.reps} · lapses ${schedule.lapses}`
    : "not scheduled";
  const best = bestLine(history.levels);
  return h(
    "section",
    { class: "side-block", "aria-labelledby": "history-heading" },
    h("h2", { id: "history-heading", class: "eyebrow" }, "history"),
    h("p", { class: "review-line" }, h("span", { class: "quiet" }, "review "), review),
    best ? h("p", { class: "best-line" }, h("span", { class: "quiet" }, "passed "), best) : null,
    history.attempts.length
      ? h("ol", { class: "plain attempts" }, ...history.attempts.map((attempt) => pastAttempt(context, slug, attempt)))
      : empty("no attempts yet", h("p", { class: "quiet" }, command(`cstudy history ${slug}`))),
  );
}

function pastAttempt(context: PageContext, slug: string, attempt: PastAttempt): HTMLElement {
  const runs = attempt.submissions.length
    ? attempt.submissions.map((run) => `${localMinute(run.submitted_at)}  submit ${run.passed}/${run.total}`)
    : attempt.test_runs.map((run) => `${localMinute(run.ran_at)}  test ${run.passed}/${run.total}`);
  const bench = attempt.bench_runs.map((run) => `${localMinute(run.ran_at)}  bench ${run.verdict}`);
  const grade = [attempt.grade, attempt.solution_revealed ? "solution" : null].filter(Boolean).join(" ");
  const files = h("div", { class: "past-files" });
  const details = h(
    "details",
    {},
    h(
      "summary",
      {},
      h("span", { class: "num" }, `#${attempt.attempt_id}`),
      ` ${attempt.language ?? "-"} · ${attempt.mode} · ${pastStatus(attempt)}`,
      h("span", { class: "quiet" }, ` · ${localMinute(attempt.started_at)}`),
      attempt.solve_s !== null ? h("span", { class: "quiet" }, ` · ${solveTime(attempt.solve_s)}`) : null,
      grade ? h("span", { class: "quiet" }, ` · ${grade}`) : null,
    ),
    runs.length || bench.length
      ? h("pre", { class: "runs" }, [...runs, ...bench].join("\n"))
      : h("p", { class: "quiet" }, "no runs recorded"),
    attempt.status === IN_PROGRESS ? h("p", {}, h("a", { href: attemptHash(attempt.attempt_id) }, "Open it in the Attempt view")) : files,
  );
  let asked = false;
  details.addEventListener("toggle", () => {
    if (!details.open || asked || attempt.status === IN_PROGRESS) return;
    asked = true;
    openLazily(context, () => import("../sheets.ts"), (module) => module.showPastFiles(context, slug, attempt, files));
  });
  return h("li", {}, details);
}
