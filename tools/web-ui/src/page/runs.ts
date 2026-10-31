/**
 * Runs on the Attempt view (docs/specs/web-ui.md#attempt-view, docs/specs/web-ui.md#runs): Run
 * tests and Submit with their options, Cancel, the results panel fed by the run's stream,
 * diagnostics as editor markers with jump-to-line, a refresh once a run opened a level, Bench as a
 * job, and run on save.
 *
 * The page never judges: every row comes from the child `cstudy` the server started. A run another
 * tab started, or the one a reload left, shows again from its stream's replay.
 */

import "./runs.css";

import { ApiError, FILE_SAVED_EVENT, type FileSaved } from "./api.ts";
import type { PageContext } from "./context.ts";
import { h } from "./dom.ts";
import { LiveStream } from "./event-stream.ts";
import { JobPanel } from "./jobs.ts";
import { noRunYet, ResultsPanel } from "./results.ts";
import { RunModel, resultsView } from "./results-model.ts";
import { diagnosticPath, diagnosticsByPath } from "./run-diagnostics.ts";
import { type Diagnostic, RUN_EVENT_TYPES, type RunEvent } from "./run-events.ts";
import { DEFAULT_OPTIONS, type RunCommandName, type RunContext, runBody, runCommand, type RunOptionsState } from "./run-options.ts";
import { RunOptionsForm } from "./run-options-form.ts";
import { failure } from "./states.ts";
import type { AttemptStatus, ProblemDocument } from "./types.ts";
import type { EditorTabs } from "./workbench.ts";

const RUN_ON_SAVE_DEBOUNCE_MS = 150;
const MAC = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.userAgent);
const RUN_KEY = MAC ? "⌘↵" : "Ctrl-Enter";
const SUBMIT_KEY = MAC ? "⌘⇧↵" : "Ctrl-Shift-Enter";
const CANCEL_QUESTION = "Cancel the run? cstudy stops it as Ctrl-C does and records nothing.";

interface RunDocument {
  readonly id: string;
  readonly state: "running" | "ended";
}

export interface RunsHost {
  readonly context: PageContext;
  readonly attemptId: number;
  readonly tabs: EditorTabs;
  /** Fetches the header, the statement and the tree again, once a run opened a level. */
  refresh(): void;
  /** Whether the attempt's tree, as it shows now, lists the file. */
  hasFile(path: string): boolean;
}

export class AttemptRuns {
  readonly toolbar: HTMLElement;
  readonly panel: HTMLElement;
  readonly #host: RunsHost;
  readonly #results: ResultsPanel;
  readonly #form: RunOptionsForm;
  readonly #bench: JobPanel;
  readonly #run: HTMLButtonElement;
  readonly #submit: HTMLButtonElement;
  readonly #cancel: HTMLButtonElement;
  readonly #toggleOptions: HTMLButtonElement;
  readonly #benchButton: HTMLButtonElement;
  readonly #cleanups: (() => void)[] = [];
  #status: AttemptStatus | null = null;
  #problem: ProblemDocument | null = null;
  #root = "";
  #options: RunOptionsState = DEFAULT_OPTIONS;
  #model: RunModel | null = null;
  #stream: LiveStream | null = null;
  #runId: string | null = null;
  #starting = false;
  #queued = false;
  #saveTimer: number | undefined;
  #refreshOnUnlock = false;
  #byPath = new Map<string, Diagnostic[]>();

  constructor(host: RunsHost) {
    this.#host = host;
    this.#run = h("button", { type: "button", class: "button primary run-button" }, h("span", { "aria-hidden": "true" }, "▶"), "Run tests", h("kbd", {}, RUN_KEY));
    this.#submit = h("button", { type: "button", class: "button run-button", hidden: true }, "Submit", h("kbd", {}, SUBMIT_KEY));
    this.#cancel = h("button", { type: "button", class: "button cancel-button", disabled: true, title: "Stop the run as Ctrl-C does (Escape in the results)" }, h("span", { "aria-hidden": "true" }, "■"), "Cancel");
    this.#toggleOptions = h("button", { type: "button", class: "button ghost", "aria-expanded": "false", "aria-controls": "run-options" }, "Run options");
    this.#benchButton = h("button", { type: "button", class: "button ghost", hidden: true }, "Bench");
    this.toolbar = h("div", { class: "run-toolbar", role: "toolbar", "aria-label": "Runs", hidden: true }, this.#run, this.#submit, this.#cancel, this.#toggleOptions, this.#benchButton);
    this.#form = new RunOptionsForm(this.#options, (options) => {
      this.#options = options;
      this.#showCommands();
    });
    this.#form.element.id = "run-options";
    this.#bench = new JobPanel(host.context);
    this.#results = new ResultsPanel(
      { jumpTarget: (diagnostic) => this.#jumpTarget(diagnostic), rerun: (id, seed) => void this.#start("test", { cases: [id], stress: 1, seed }) },
      [this.#form.element, this.#bench.element],
    );
    this.panel = this.#results.element;
    this.#run.addEventListener("click", () => void this.#start("test"));
    this.#submit.addEventListener("click", () => void this.#start("submit"));
    this.#cancel.addEventListener("click", () => void this.#cancelRun());
    this.#toggleOptions.addEventListener("click", () => this.#flipOptions());
    this.#benchButton.addEventListener("click", () => void this.#startBench());
    this.#results.body.addEventListener("keydown", (event) => this.#onResultsKey(event));
    this.#listen(document, "keydown", (event) => this.#onKey(event as KeyboardEvent), true);
    this.#listen(window, FILE_SAVED_EVENT, (event) => this.#onSaved((event as CustomEvent<FileSaved>).detail));
    this.#cleanups.push(host.tabs.onEditor((path, editor) => editor.setDiagnostics(this.#byPath.get(path) ?? [])));
  }

  /** Takes the attempt as the view loaded it, or as it is after a level opened. */
  async setAttempt(status: AttemptStatus, root: string): Promise<void> {
    const first = this.#status === null;
    this.#status = status;
    this.#root = root;
    if (status.kind === "item") {
      this.#results.show(null, [h("p", { class: "quiet" }, "Items have no runs: answer in the notes.")]);
      return;
    }
    if (first) this.#problem = await this.#context.api.get<ProblemDocument>(`/api/v1/problems/${encodeURIComponent(status.slug)}`).catch(() => null);
    this.toolbar.hidden = false;
    this.#submit.hidden = status.kind !== "project";
    this.#benchButton.hidden = !(this.#problem?.bench && status.language);
    this.#form.configure(this.#runContext(), this.#options);
    this.#showCommands();
    if (first) await this.#showLatestRun(status);
  }

  destroy(): void {
    this.#stream?.close();
    this.#bench.destroy();
    this.#results.destroy();
    window.clearTimeout(this.#saveTimer);
    for (const cleanup of this.#cleanups) cleanup();
  }

  get #context(): PageContext {
    return this.#host.context;
  }

  get #running(): boolean {
    return this.#starting || this.#stream !== null;
  }

  #runContext(): RunContext {
    const status = this.#status!;
    return {
      slug: status.slug,
      kind: status.kind,
      language: status.language,
      levels: status.levels,
      oracle: this.#problem?.oracle ?? false,
      typecheck: this.#context.preferences().typecheck,
    };
  }

  /** The newest run of the attempt still in the server, live or replayed; else what the CLI recorded. */
  async #showLatestRun(status: AttemptStatus): Promise<void> {
    const runs = await this.#context.api.get<RunDocument[]>(`/api/v1/runs?attempt_id=${this.#host.attemptId}`).catch(() => []);
    const latest = runs[0];
    if (latest) {
      this.#attach(latest.id, latest.state === "running");
      return;
    }
    this.#results.show(null, noRunYet(runCommand("test", this.#options, this.#runContext()), status.last_test_run));
  }

  async #start(command: RunCommandName, change: Partial<RunOptionsState> = {}): Promise<void> {
    if (this.#running || this.#status === null || this.#status.kind === "item") return;
    if (command === "submit" && this.#status.kind !== "project") return;
    const options = { ...this.#options, ...change };
    const context = this.#runContext();
    this.#starting = true;
    this.#showState();
    try {
      const { id } = await this.#context.api.post<{ id: string }>("/api/v1/runs", runBody(this.#host.attemptId, command, options, context));
      this.#context.shell.announce(`running ${runCommand(command, options, context)}`);
      this.#attach(id, true);
    } catch (error) {
      const active = error instanceof ApiError && error.code === "conflict" ? error.details["run"] : undefined;
      if (typeof active === "string") {
        this.#attach(active, true);
        return;
      }
      this.#results.show(null, [failure(error)]);
    } finally {
      this.#starting = false;
      this.#showState();
    }
  }

  #attach(runId: string, live: boolean): void {
    this.#stream?.close();
    this.#runId = runId;
    this.#refreshOnUnlock = live;
    this.#model = new RunModel();
    this.#results.show(this.#model);
    this.#stream = new LiveStream(`/api/v1/runs/${runId}/events`, RUN_EVENT_TYPES, {
      restart: () => {
        this.#model = new RunModel();
        this.#results.show(this.#model);
      },
      message: (_name, data) => this.#onEvent(data as RunEvent),
      closed: (closed) => {
        this.#stream = null;
        this.#model?.close(closed);
        this.#results.update();
        this.#ended();
      },
      lost: () => {
        this.#stream = null;
        this.#results.show(null, [h("p", { class: "quiet" }, "The server no longer keeps this run, as after a restart; run the tests again.")]);
        this.#showState();
      },
    });
    this.#showState();
  }

  #onEvent(event: RunEvent): void {
    const model = this.#model;
    if (!model) return;
    model.apply(event);
    this.#results.update();
    if (event.type === "run_start") this.#markDiagnostics([]);
    if (event.type === "diagnostic") this.#markDiagnostics(model.diagnostics);
  }

  #ended(): void {
    this.#showState();
    const model = this.#model;
    if (model) {
      const summary = resultsView(model, false).summary;
      this.#context.shell.announce(summary ? `run ended: ${summary.text}` : "run ended");
      if (model.unlocked && this.#refreshOnUnlock) this.#host.refresh();
    }
    if (this.#queued) {
      this.#queued = false;
      void this.#start("test");
    }
  }

  async #cancelRun(): Promise<void> {
    if (this.#runId === null || this.#stream === null) return;
    this.#cancel.disabled = true;
    try {
      await this.#context.api.post(`/api/v1/runs/${this.#runId}/cancel`, {});
      this.#context.shell.announce("cancelling the run");
    } catch (error) {
      if (!(error instanceof ApiError && error.code === "conflict")) this.#results.show(this.#model, [failure(error)]);
    }
  }

  async #startBench(): Promise<void> {
    const status = this.#status;
    if (!status?.language) return;
    await this.#bench.start({ command: "bench", slug: status.slug, language: status.language }, `cstudy bench ${status.slug} --lang ${status.language}`);
  }

  /** Replaces every editor's markers with the run's diagnostics of its file. */
  #markDiagnostics(diagnostics: readonly Diagnostic[]): void {
    this.#byPath = diagnosticsByPath(diagnostics, this.#status?.kind ?? "", this.#root);
    for (const [path, editor] of this.#host.tabs.editors()) editor.setDiagnostics(this.#byPath.get(path) ?? []);
  }

  #jumpTarget(diagnostic: Diagnostic): (() => void) | null {
    const path = diagnosticPath(diagnostic.file, this.#status?.kind ?? "", this.#root);
    if (path === null || !this.#host.hasFile(path)) return null;
    return () => {
      const tabs = this.#host.tabs;
      void tabs.open(path).then(() => tabs.editors().get(path)?.jumpTo(diagnostic.line ?? 1, diagnostic.column));
    };
  }

  /** Run on save: a test run 150 ms after a save, or one more after the run in progress. */
  #onSaved(saved: FileSaved): void {
    if (saved.attemptId !== this.#host.attemptId || !this.#context.preferences().run_on_save) return;
    window.clearTimeout(this.#saveTimer);
    this.#saveTimer = window.setTimeout(() => {
      if (this.#running) this.#queued = true;
      else void this.#start("test");
    }, RUN_ON_SAVE_DEBOUNCE_MS);
  }

  #onKey(event: KeyboardEvent): void {
    if (event.key !== "Enter" || !(event.metaKey || event.ctrlKey) || event.altKey) return;
    event.preventDefault();
    event.stopPropagation();
    void this.#start(event.shiftKey ? "submit" : "test");
  }

  #onResultsKey(event: KeyboardEvent): void {
    if (event.key !== "Escape" || this.#stream === null) return;
    event.preventDefault();
    if (window.confirm(CANCEL_QUESTION)) void this.#cancelRun();
  }

  #flipOptions(): void {
    const open = this.#form.element.hidden;
    this.#form.element.hidden = !open;
    this.#toggleOptions.setAttribute("aria-expanded", String(open));
  }

  #showState(): void {
    const running = this.#running;
    this.#run.disabled = running;
    this.#submit.disabled = running;
    this.#cancel.disabled = this.#stream === null;
    this.toolbar.classList.toggle("is-running", running);
  }

  /** Each button names the command it runs and its shortcut. */
  #showCommands(): void {
    if (this.#status === null) return;
    const context = this.#runContext();
    this.#run.title = `${runCommand("test", this.#options, context)} (${RUN_KEY})`;
    this.#submit.title = `${runCommand("submit", this.#options, context)} (${SUBMIT_KEY})`;
    if (this.#status.language) this.#benchButton.title = `cstudy bench ${this.#status.slug} --lang ${this.#status.language}`;
  }

  #listen(target: EventTarget, name: string, listener: (event: Event) => void, capture = false): void {
    target.addEventListener(name, listener, capture);
    this.#cleanups.push(() => target.removeEventListener(name, listener, capture));
  }
}
