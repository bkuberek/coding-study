/**
 * The results panel (docs/specs/web-ui.md#attempt-view): the frame a run is drawn into as it
 * streams, and what it shows before there is a run. The panel redraws at most once a frame, so a
 * stress run's many events cost one layout each; nothing it draws takes the focus. The code that
 * draws a run (`results-draw.ts`) arrives with the run session, fetched the first time a run
 * shows, so the page loads less before a file is editable (NFR-12).
 */

import { badge, command, h } from "./dom.ts";
import type { RunModel } from "./results-model.ts";
import type { Diagnostic } from "./run-events.ts";

export interface ResultsActions {
  /** Opens the diagnostic's file at its line; null when it marks no file of the attempt. */
  jumpTarget(diagnostic: Diagnostic): (() => void) | null;
  /** Runs one stress case once more with the seed of a failing run. */
  rerun(caseId: string, seed: number): void;
}

/** The elements of the panel a run is drawn into. */
export interface ResultsParts {
  readonly title: HTMLElement;
  readonly progress: HTMLProgressElement;
  readonly body: HTMLElement;
}

/** `drawRun` of `results-draw.ts`. */
export type RunDrawer = (parts: ResultsParts, model: RunModel, showAll: boolean, actions: ResultsActions) => void;

export class ResultsPanel {
  readonly element: HTMLElement;
  readonly #title: HTMLElement;
  readonly #progress: HTMLProgressElement;
  readonly #body: HTMLElement;
  readonly #showAll: HTMLInputElement;
  #drawer: RunDrawer | null = null;
  #actions: ResultsActions | null = null;
  #model: RunModel | null = null;
  #placeholder: readonly Node[] = [];
  #job: HTMLElement | null = null;
  #frame = 0;

  constructor() {
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
      this.#body,
    );
  }

  /** The element that takes Escape to cancel a run. */
  get body(): HTMLElement {
    return this.#body;
  }

  /** Puts the run options form above the job and the results. */
  addOptions(form: HTMLElement): void {
    (this.#job ?? this.#body).before(form);
  }

  /** Puts a job's panel above the results, under the run options. */
  addJob(job: HTMLElement): void {
    this.#body.before(job);
    this.#job = job;
  }

  /** Takes the way a run is drawn, which arrives with the first run; until then only placeholders show. */
  bind(drawer: RunDrawer, actions: ResultsActions): void {
    this.#drawer = drawer;
    this.#actions = actions;
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
    if (!model || !this.#drawer || !this.#actions) {
      this.#title.textContent = "";
      this.#progress.hidden = true;
      this.#body.replaceChildren(...this.#placeholder);
      return;
    }
    this.#drawer({ title: this.#title, progress: this.#progress, body: this.#body }, model, this.#showAll.checked, this.#actions);
  }
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
