/**
 * How a run is drawn in the results panel (docs/specs/web-ui.md#attempt-view): its rows, in the
 * terminal report's order and words, from the run's model. It is a chunk of its own, fetched with
 * the first run the panel shows (`results-kit.ts`), so the page loads less before a file is
 * editable (NFR-12).
 */

import { badge, h } from "./dom.ts";
import { caseFacts, caseLines, durationText, levelLine, stressFacts, testName } from "./results-format.ts";
import { type CaseRow, headerText, type RowStatus, type RunModel, resultsView, STATUS_WORDS, type StressGroup, type TestRow, type ViewItem } from "./results-model.ts";
import type { ResultsActions, ResultsParts } from "./results.ts";
import type { Diagnostic } from "./run-events.ts";

const FOLLOW_SLACK_PX = 8;
const GLYPHS: Readonly<Record<RowStatus, string>> = {
  pass: "✓",
  fail: "✕",
  error: "!",
  timeout: "⧗",
  tle: "⧗",
  invalid: "?",
  stalled: "‖",
  not_run: "–",
  skip: "↷",
  running: "▸",
};
const TONES: Readonly<Record<RowStatus, string>> = {
  pass: "ok",
  fail: "fail",
  error: "fail",
  timeout: "fail",
  tle: "warn",
  invalid: "fail",
  stalled: "fail",
  not_run: "quiet",
  skip: "quiet",
  running: "info",
};

/** Draws `model` into the panel's title, progress bar and body. */
export function drawRun(parts: ResultsParts, model: RunModel, showAll: boolean, actions: ResultsActions): void {
  const view = resultsView(model, showAll);
  parts.title.textContent = model.start ? headerText(model.start) : "starting…";
  drawProgress(parts.progress, view.progress, model);
  const body = parts.body;
  // Like a terminal, the panel follows the newest line while it is scrolled to the end.
  const following = body.scrollTop + body.clientHeight >= body.scrollHeight - FOLLOW_SLACK_PX;
  body.replaceChildren(
    ...(model.build ? [buildLine(model.build)] : []),
    h("ol", { class: "result-rows" }, ...view.items.map((item) => itemRow(item, model, actions))),
    ...view.running.map((id) => h("p", { class: "result-running" }, badge(GLYPHS.running, STATUS_WORDS.running, "info"), " ", h("span", { class: "result-id" }, id))),
    ...(view.notice ? [h("p", { class: "result-notice" }, view.notice, "…")] : []),
    ...(model.diagnostics.length ? [diagnosticsBlock(model.diagnostics, actions)] : []),
    ...(model.unlocked ? [unlockedBanner(model)] : []),
    ...(model.perf ? [perfBlock(model)] : []),
    ...(view.summary ? [summaryBlock(view.summary)] : []),
  );
  if (following) body.scrollTop = body.scrollHeight;
}

/** A bar against the run's plan while it runs; without a plan, as for a project's suite, it only moves. */
function drawProgress(bar: HTMLProgressElement, progress: { readonly done: number; readonly planned: number | null }, model: RunModel): void {
  bar.hidden = model.closed !== null;
  if (progress.planned) {
    bar.max = progress.planned;
    bar.value = Math.min(progress.done, progress.planned);
  } else {
    bar.removeAttribute("value");
  }
}

function itemRow(item: ViewItem, model: RunModel, actions: ResultsActions): HTMLElement {
  switch (item.kind) {
    case "case":
      return caseItem(item.row);
    case "test":
      return testItem(item.row);
    case "file":
      return h("li", { class: "result-file" }, item.path);
    case "count":
      return h("li", { class: `result-row result-count status-${item.status}` }, statusBadge(item.status), h("span", { class: "result-id" }, item.text));
    case "more":
      return h("li", { class: "result-row result-more" }, item.text);
    case "stress":
      return stressItem(item.group, model, actions);
    case "level":
      return h(
        "li",
        { class: `result-row result-level status-${item.result.status}` },
        h("span", { class: "result-level-name" }, `level ${item.result.level}`),
        statusBadge(item.result.status),
        h("span", { class: "result-facts" }, levelLine(item.result, model.start?.mode === "mock")),
      );
  }
}

function stressItem(group: StressGroup, model: RunModel, actions: ResultsActions): HTMLElement {
  const status: RowStatus = group.result?.status ?? "running";
  const planned = model.start?.planned?.stress?.runs ?? group.runs.length;
  const dots = Array.from({ length: Math.max(planned, group.runs.length) }, (_, run) => {
    const ran = group.runs[run];
    return h("span", { class: `stress-dot dot-${ran ?? "pending"}`, title: `run ${run}: ${ran ? STATUS_WORDS[ran] : "pending"}` });
  });
  const failures = group.result?.failures ?? group.failures;
  return h(
    "li",
    { class: `result-row result-stress status-${status}` },
    statusBadge(status),
    h("span", { class: "result-id" }, group.id),
    h("span", { class: "result-facts" }, stressFacts(group.variant, group.result)),
    h("span", { class: "stress-dots", "aria-hidden": "true" }, ...dots),
    failures.length
      ? h(
          "ul",
          { class: "stress-failures" },
          ...failures.slice(0, 3).map((failure) => {
            const rerun = h("button", { type: "button", class: "ghost", title: `cstudy test --case ${group.id} --stress 1 --seed ${failure.seed}` }, "Rerun");
            rerun.addEventListener("click", () => actions.rerun(group.id, failure.seed));
            return h("li", {}, `run ${failure.run} · seed ${failure.seed}  `, h("span", { class: "result-reason" }, failure.reasons.join("; ") || failure.status), " ", rerun);
          }),
        )
      : null,
  );
}

function diagnosticsBlock(diagnostics: readonly Diagnostic[], actions: ResultsActions): HTMLElement {
  return h(
    "section",
    { class: "result-diagnostics", "aria-label": "Diagnostics" },
    h("h3", { class: "eyebrow" }, `diagnostics · ${diagnostics.length}`, h("span", { class: "quiet" }, " · F8 in the editor goes to the next")),
    h(
      "ul",
      {},
      ...diagnostics.map((diagnostic) => {
        const place = [diagnostic.file, diagnostic.line, diagnostic.column].filter((part) => part !== null).join(":");
        const jump = actions.jumpTarget(diagnostic);
        const label = h("span", { class: "diagnostic-place" }, place || diagnostic.source);
        return h(
          "li",
          { class: `diagnostic severity-${diagnostic.severity}` },
          badge(diagnostic.severity === "error" ? "✕" : "!", diagnostic.severity, diagnostic.severity === "error" ? "fail" : "warn"),
          " ",
          jump ? jumpButton(label, jump, diagnostic) : label,
          " ",
          h("span", { class: "diagnostic-message" }, diagnostic.code ? `${diagnostic.code}: ${diagnostic.message}` : diagnostic.message),
        );
      }),
    ),
  );
}

function jumpButton(label: HTMLElement, jump: () => void, diagnostic: Diagnostic): HTMLButtonElement {
  const button = h("button", { type: "button", class: "diagnostic-jump", title: `Open ${diagnostic.file} at line ${diagnostic.line ?? 1}` }, label);
  button.addEventListener("click", jump);
  return button;
}

function statusBadge(status: RowStatus): HTMLElement {
  return badge(GLYPHS[status], STATUS_WORDS[status], TONES[status]);
}

function caseItem(row: CaseRow): HTMLElement {
  return resultRow(row.status, row.id, caseFacts(row), caseLines(row.result));
}

function testItem(row: TestRow): HTMLElement {
  const origin = row.result?.origin;
  const tag = origin === "starter" || origin === "yours" ? origin : "";
  const facts = [tag, row.result ? durationText(row.result.duration_ns) : ""].filter(Boolean).join(" · ");
  return resultRow(row.status, testName(row.id), facts, caseLines(row.result));
}

function resultRow(status: RowStatus, id: string, facts: string, lines: readonly [string, string][]): HTMLElement {
  return h(
    "li",
    { class: `result-row status-${status}` },
    statusBadge(status),
    h("span", { class: "result-id" }, id),
    h("span", { class: "result-facts" }, facts),
    lines.length ? h("dl", { class: "result-details" }, ...lines.flatMap(([label, text]) => [h("dt", {}, label), h("dd", {}, text)])) : null,
  );
}

function buildLine(build: { readonly seconds: number; readonly note: string | null }): HTMLElement {
  return h("p", { class: "result-build" }, h("span", { class: "result-label" }, "build"), `${build.seconds.toFixed(1)}s`, build.note ? ` (${build.note})` : " · failed");
}

function unlockedBanner(model: RunModel): HTMLElement {
  const opened = model.unlocked!;
  const last = model.start?.levels?.last;
  return h(
    "div",
    { class: "result-unlocked", role: "status" },
    h("p", { class: "result-unlocked-title" }, badge("◆", `level ${opened.level}${last ? ` of ${last}` : ""} unlocked`, "ok"), " ", opened.title),
    opened.methods.length ? h("p", {}, h("span", { class: "result-label" }, "add"), opened.methods.join(", ")) : null,
    opened.tests ? h("p", {}, h("span", { class: "result-label" }, "tests"), `${opened.tests.path} (${opened.tests.count} tests)`) : null,
    h("p", {}, h("span", { class: "result-label" }, "statement"), `${opened.statement} (updated)`),
  );
}

function perfBlock(model: RunModel): HTMLElement {
  const perf = model.perf!;
  return h(
    "div",
    { class: "result-perf" },
    h("p", {}, h("span", { class: "result-label" }, "perf"), perf.text),
    ...perf.warnings.map((warning) => h("p", { class: "tone-warn" }, "warning ", warning)),
    perf.wrong_answer ? h("p", { class: "tone-fail" }, perf.wrong_answer) : null,
  );
}

function summaryBlock(summary: { readonly tone: string; readonly text: string; readonly notes: readonly string[] }): HTMLElement {
  return h(
    "div",
    { class: `result-summary tone-${summary.tone}` },
    h("p", { class: "result-summary-text" }, summary.text),
    ...summary.notes.map((note) => h("p", { class: "result-note" }, note)),
  );
}
