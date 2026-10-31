/**
 * The results panel (docs/specs/web-ui.md#attempt-view): a run drawn from its model as it streams,
 * in the terminal report's order and words. The panel redraws at most once a frame, so a stress run's
 * many events cost one layout each; nothing it draws takes the focus.
 */

import { badge, command, h } from "./dom.ts";
import { caseFacts, caseLines, durationText, levelLine, stressFacts, testName } from "./results-format.ts";
import { type CaseRow, headerText, type RowStatus, type RunModel, resultsView, STATUS_WORDS, type StressGroup, type TestRow, type ViewItem } from "./results-model.ts";
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

export interface ResultsActions {
  /** Opens the diagnostic's file at its line; null when it marks no file of the attempt. */
  jumpTarget(diagnostic: Diagnostic): (() => void) | null;
  /** Runs one stress case once more with the seed of a failing run. */
  rerun(caseId: string, seed: number): void;
}

export class ResultsPanel {
  readonly element: HTMLElement;
  readonly #title: HTMLElement;
  readonly #progress: HTMLProgressElement;
  readonly #body: HTMLElement;
  readonly #showAll: HTMLInputElement;
  readonly #actions: ResultsActions;
  #model: RunModel | null = null;
  #placeholder: readonly Node[] = [];
  #frame = 0;

  constructor(actions: ResultsActions, extra: readonly Node[]) {
    this.#actions = actions;
    this.#title = h("span", { class: "results-title" });
    this.#showAll = h("input", { type: "checkbox", id: "results-show-all" });
    this.#showAll.addEventListener("change", () => this.update());
    this.#progress = h("progress", { class: "results-progress", "aria-label": "Run progress", hidden: true });
    this.#body = h("div", { class: "results-body", tabindex: "0", "aria-label": "Run results" });
    this.element = h(
      "section",
      { class: "results", "aria-label": "Results" },
      h(
        "header",
        { class: "results-head" },
        h("h2", { class: "eyebrow" }, "results"),
        this.#title,
        h("span", { class: "spacer" }),
        h("label", { class: "show-all", for: "results-show-all" }, this.#showAll, "show all"),
      ),
      this.#progress,
      ...extra,
      this.#body,
    );
  }

  /** The element that takes Escape to cancel a run. */
  get body(): HTMLElement {
    return this.#body;
  }

  /** Draws `model`, or `placeholder` while no run is shown. */
  show(model: RunModel | null, placeholder: readonly Node[] = []): void {
    this.#model = model;
    this.#placeholder = placeholder;
    this.update();
  }

  /** Redraws on the next frame. */
  update(): void {
    if (this.#frame) return;
    this.#frame = requestAnimationFrame(() => {
      this.#frame = 0;
      this.#draw();
    });
  }

  destroy(): void {
    cancelAnimationFrame(this.#frame);
  }

  #draw(): void {
    const model = this.#model;
    if (!model) {
      this.#title.textContent = "";
      this.#progress.hidden = true;
      this.#body.replaceChildren(...this.#placeholder);
      return;
    }
    const view = resultsView(model, this.#showAll.checked);
    this.#title.textContent = model.start ? headerText(model.start) : "starting…";
    this.#drawProgress(view.progress, model);
    const body = this.#body;
    // Like a terminal, the panel follows the newest line while it is scrolled to the end.
    const following = body.scrollTop + body.clientHeight >= body.scrollHeight - FOLLOW_SLACK_PX;
    body.replaceChildren(
      ...(model.build ? [buildLine(model.build)] : []),
      h("ol", { class: "result-rows" }, ...view.items.map((item) => this.#item(item, model))),
      ...view.running.map((id) => h("p", { class: "result-running" }, badge(GLYPHS.running, STATUS_WORDS.running, "info"), " ", h("span", { class: "result-id" }, id))),
      ...(view.notice ? [h("p", { class: "result-notice" }, view.notice, "…")] : []),
      ...(model.diagnostics.length ? [this.#diagnostics(model.diagnostics)] : []),
      ...(model.unlocked ? [unlockedBanner(model)] : []),
      ...(model.perf ? [perfBlock(model)] : []),
      ...(view.summary ? [summaryBlock(view.summary)] : []),
    );
    if (following) body.scrollTop = body.scrollHeight;
  }

  /** A bar against the run's plan while it runs; without a plan, as for a project's suite, it only moves. */
  #drawProgress(progress: { readonly done: number; readonly planned: number | null }, model: RunModel): void {
    this.#progress.hidden = model.closed !== null;
    if (progress.planned) {
      this.#progress.max = progress.planned;
      this.#progress.value = Math.min(progress.done, progress.planned);
    } else {
      this.#progress.removeAttribute("value");
    }
  }

  #item(item: ViewItem, model: RunModel): HTMLElement {
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
        return this.#stressItem(item.group, model);
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

  #stressItem(group: StressGroup, model: RunModel): HTMLElement {
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
              rerun.addEventListener("click", () => this.#actions.rerun(group.id, failure.seed));
              return h("li", {}, `run ${failure.run} · seed ${failure.seed}  `, h("span", { class: "result-reason" }, failure.reasons.join("; ") || failure.status), " ", rerun);
            }),
          )
        : null,
    );
  }

  #diagnostics(diagnostics: readonly Diagnostic[]): HTMLElement {
    return h(
      "section",
      { class: "result-diagnostics", "aria-label": "Diagnostics" },
      h("h3", { class: "eyebrow" }, `diagnostics · ${diagnostics.length}`, h("span", { class: "quiet" }, " · F8 in the editor goes to the next")),
      h(
        "ul",
        {},
        ...diagnostics.map((diagnostic) => {
          const place = [diagnostic.file, diagnostic.line, diagnostic.column].filter((part) => part !== null).join(":");
          const jump = this.#actions.jumpTarget(diagnostic);
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

/** What the panel shows before the page runs anything: the latest recorded run, and how to run one. */
export function noRunYet(testCommand: string, lastRun: { readonly total: number; readonly passed: number; readonly ran_at: string } | null): Node[] {
  return [
    lastRun
      ? h(
          "p",
          { class: "last-run" },
          badge(lastRun.passed === lastRun.total ? "✓" : "✕", `${lastRun.passed}/${lastRun.total} passed`, lastRun.passed === lastRun.total ? "ok" : "fail"),
          h("span", { class: "quiet" }, ` latest cstudy test, ${new Date(lastRun.ran_at).toLocaleString()}`),
        )
      : h("p", { class: "quiet" }, "No test run yet."),
    h("p", { class: "quiet" }, "Run the tests with the button above or ⌘↵ (Ctrl-Enter): ", command(testCommand)),
  ];
}
