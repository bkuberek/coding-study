/**
 * The Problem view (docs/specs/web-ui.md#problem-view): the header, the `cstudy show` statement,
 * how to start or resume it, its approaches, and its `cstudy history`.
 */

import { startCommand } from "../commands.ts";
import type { Cleanup, PageContext } from "../context.ts";
import { badge, command, h, rendered } from "../dom.ts";
import { localMinute, problemBadge, solveTime } from "../format.ts";
import { attemptHash } from "../routes.ts";
import { empty, loading, showFailure } from "../states.ts";
import type { History, PastAttempt, ProblemDocument, Rendered } from "../types.ts";

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
  ])
    .then(([problem, statement, history]) => {
      page.removeAttribute("aria-busy");
      page.replaceChildren(header(problem), h("div", { class: "problem-grid" }, statementPane(statement), side(context, problem, history)));
      shell.setStatus({ mode: "PROBLEM", where: `${problem.slug} · ${problem.kind} · ${problem.difficulty}` });
      document.title = `${problem.title} · cstudy`;
    })
    .catch((error: unknown) => showFailure(page, error));
  return () => {};
}

function header(problem: ProblemDocument): HTMLElement {
  const status = problemBadge(problem.status);
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

function side(context: PageContext, problem: ProblemDocument, history: History): HTMLElement {
  return h(
    "aside",
    { class: "problem-side", "aria-label": "Practice" },
    practice(context, problem),
    problem.approaches.length ? approaches(problem) : null,
    historySection(problem.slug, history),
  );
}

function practice(context: PageContext, problem: ProblemDocument): HTMLElement {
  const language = problemLanguage(context, problem);
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
    h("p", { class: "quiet" }, resumes.length ? "or start another in the terminal:" : "start it in the terminal:"),
    h("p", {}, command(startCommand(problem.slug, language))),
    problem.hints_total ? h("p", { class: "quiet" }, `${problem.hints_total} hints · any hint caps the review grade at ok`) : null,
    problem.levels ? h("p", { class: "quiet" }, `${problem.levels.last} levels, each opened by passing the one before`) : null,
  );
}

/** The language `cstudy start` would use: the only one, or `default_lang` when the problem has it. */
function problemLanguage(context: PageContext, problem: ProblemDocument): string | null {
  if (problem.languages.length === 0) return null;
  if (problem.languages.length === 1) return problem.kind === "project" ? null : (problem.languages[0] ?? null);
  const preferred = context.session.default_lang;
  return problem.languages.includes(preferred) ? preferred : (problem.languages[0] ?? null);
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

function historySection(slug: string, history: History): HTMLElement {
  const schedule = history.schedule;
  const review = schedule
    ? `due ${schedule.due_on} · interval ${schedule.interval_days}d · ease ${schedule.ease.toFixed(2)} · reps ${schedule.reps} · lapses ${schedule.lapses}`
    : "not scheduled";
  return h(
    "section",
    { class: "side-block", "aria-labelledby": "history-heading" },
    h("h2", { id: "history-heading", class: "eyebrow" }, "history"),
    h("p", { class: "review-line" }, h("span", { class: "quiet" }, "review "), review),
    history.attempts.length
      ? h("ol", { class: "plain attempts" }, ...history.attempts.map(pastAttempt))
      : empty("no attempts yet", h("p", { class: "quiet" }, command(`cstudy history ${slug}`))),
  );
}

function pastAttempt(attempt: PastAttempt): HTMLElement {
  const runs = attempt.submissions.length
    ? attempt.submissions.map((run) => `${localMinute(run.submitted_at)}  submit ${run.passed}/${run.total}`)
    : attempt.test_runs.map((run) => `${localMinute(run.ran_at)}  test ${run.passed}/${run.total}`);
  const bench = attempt.bench_runs.map((run) => `${localMinute(run.ran_at)}  bench ${run.verdict}`);
  const grade = [attempt.grade, attempt.solution_revealed ? "solution" : null].filter(Boolean).join(" ");
  return h(
    "li",
    {},
    h(
      "details",
      {},
      h(
        "summary",
        {},
        h("span", { class: "num" }, `#${attempt.attempt_id}`),
        ` ${attempt.language ?? "-"} · ${attempt.mode} · ${attempt.status}`,
        h("span", { class: "quiet" }, ` · ${localMinute(attempt.started_at)}`),
        attempt.solve_s !== null ? h("span", { class: "quiet" }, ` · ${solveTime(attempt.solve_s)}`) : null,
        grade ? h("span", { class: "quiet" }, ` · ${grade}`) : null,
      ),
      runs.length || bench.length
        ? h("pre", { class: "runs" }, [...runs, ...bench].join("\n"))
        : h("p", { class: "quiet" }, "no runs recorded"),
    ),
  );
}
