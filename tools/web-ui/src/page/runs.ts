/**
 * Runs on the Attempt view (docs/specs/web-ui.md#attempt-view, docs/specs/web-ui.md#runs): Run
 * tests and Submit with their options, Cancel, the results panel fed by the run's stream,
 * diagnostics as editor markers with jump-to-line, a refresh once a run opened a level, Bench as a
 * job, and run on save.
 *
 * The page never judges: every row comes from the child `cstudy` the server started. A run another
 * tab started, or the one a reload left, shows again from its stream's replay.
 *
 * This module is what the page loads with the view: the toolbar, the frame of the results panel,
 * the shortcuts and run on save. Streaming and drawing a run, Cancel, the options form and Bench
 * are the run session (`run-session.ts`) and chunks of their own, fetched the first time a run
 * starts or shows, so the page loads less before a file is editable (NFR-12).
 */

import { FILE_SAVED_EVENT, type FileSaved } from "./api.ts";
import type { PageContext } from "./context.ts";
import { h } from "./dom.ts";
import { fetchChunk } from "./lazy.ts";
import { noRunYet, ResultsPanel } from "./results.ts";
import { DEFAULT_OPTIONS, type RunCommandName, type RunContext, runCommand, type RunOptionsState } from "./run-options.ts";
import type { RunSession } from "./run-session.ts";
import type { AttemptStatus, ProblemDocument } from "./types.ts";
import type { EditorTabs } from "./workbench.ts";

const RUN_ON_SAVE_DEBOUNCE_MS = 150;

/** A save, as its notice names it. */
function savedKey(path: string, sha256: string | null): string {
  return `${path}\n${sha256 ?? ""}`;
}
const MAC = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.userAgent);
const RUN_KEY = MAC ? "⌘↵" : "Ctrl-Enter";
const SUBMIT_KEY = MAC ? "⌘⇧↵" : "Ctrl-Shift-Enter";

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

export interface RunButtons {
  readonly run: HTMLButtonElement;
  readonly submit: HTMLButtonElement;
  readonly cancel: HTMLButtonElement;
  readonly options: HTMLButtonElement;
  readonly bench: HTMLButtonElement;
}

/** What the run session uses of the toolbar and of the attempt the view showed. */
export interface RunShell {
  readonly host: RunsHost;
  readonly toolbar: HTMLElement;
  readonly buttons: RunButtons;
  readonly results: ResultsPanel;
  readonly status: AttemptStatus | null;
  /** The attempt's folder, which the files of a run's diagnostics are relative to. */
  readonly root: string;
  /** The Run options form's state, which both Run tests and Submit take. */
  options: RunOptionsState;
  runContext(): RunContext;
  showCommands(): void;
  /** Drops the run on save of saves just made, which the run about to start holds. */
  forgetSaves(): void;
}

export class AttemptRuns implements RunShell {
  readonly host: RunsHost;
  readonly toolbar: HTMLElement;
  readonly buttons: RunButtons;
  readonly results = new ResultsPanel();
  readonly panel: HTMLElement;
  options: RunOptionsState = DEFAULT_OPTIONS;
  readonly #cleanups: (() => void)[] = [];
  #status: AttemptStatus | null = null;
  #problem: ProblemDocument | null = null;
  #problemRead: Promise<void> | null = null;
  #root = "";
  #session: Promise<RunSession | null> | null = null;
  #saveTimer: number | undefined;
  #destroyed = false;
  #frozen = false;
  /** Whether the panel shows the run `cstudy test` last recorded, which a refresh redraws. */
  #showsRecorded = false;
  /** The saves this page made and has not heard back as notices yet, by `savedKey`. */
  readonly #ownSaves = new Set<string>();

  constructor(host: RunsHost) {
    this.host = host;
    const run = h("button", { type: "button", class: "button primary run-button" }, h("span", { "aria-hidden": "true" }, "▶"), "Run tests", h("kbd", {}, RUN_KEY));
    const submit = h("button", { type: "button", class: "button run-button", hidden: true }, "Submit", h("kbd", {}, SUBMIT_KEY));
    const cancel = h("button", { type: "button", class: "button cancel-button", disabled: true, title: "Stop the run as Ctrl-C does (Escape in the results)" }, h("span", { "aria-hidden": "true" }, "■"), "Cancel");
    const options = h("button", { type: "button", class: "button ghost", "aria-expanded": "false" }, "Run options");
    const bench = h("button", { type: "button", class: "button ghost", hidden: true }, "Bench");
    this.buttons = { run, submit, cancel, options, bench };
    this.toolbar = h("div", { class: "run-toolbar", role: "toolbar", "aria-label": "Runs", hidden: true }, run, submit, cancel, options, bench);
    this.panel = this.results.element;
    run.addEventListener("click", () => void this.#use((session) => session.start("test")));
    submit.addEventListener("click", () => void this.#use((session) => session.start("submit")));
    cancel.addEventListener("click", () => void this.#use((session) => session.cancel()));
    options.addEventListener("click", () => void this.#use((session) => session.flipOptions()));
    bench.addEventListener("click", () => void this.#use((session) => session.startBench()));
    this.#listen(document, "keydown", (event) => this.#onKey(event as KeyboardEvent), true);
    this.#listen(window, FILE_SAVED_EVENT, (event) => this.#onSaved((event as CustomEvent<FileSaved>).detail));
  }

  get status(): AttemptStatus | null {
    return this.#status;
  }

  get root(): string {
    return this.#root;
  }

  /** Takes the attempt as the view loaded it, or as it is after a level opened or a change from
   * elsewhere; a panel that shows the run `cstudy test` last recorded shows the newest one. */
  async setAttempt(status: AttemptStatus, root: string): Promise<void> {
    const first = this.#status === null;
    this.#status = status;
    this.#root = root;
    if (status.kind === "item") {
      this.results.show(null, [h("p", { class: "quiet" }, "Items have no runs: answer in the notes.")]);
      return;
    }
    await this.showToolbar(status);
    this.showCommands();
    if (first) await this.#showLatestRun(status);
    else if (this.#showsRecorded) this.#showRecorded(status);
    else void this.#session?.then((session) => session?.configure());
  }

  /** Shows the buttons the attempt's kind has, reading once what Bench needs of the problem. The
   * view waits for it before its first draw: the toolbar shown later would make the header taller
   * and move the file tree under a pointer about to click it, which then clicks nothing. */
  async showToolbar(status: AttemptStatus): Promise<void> {
    if (status.kind === "item") return;
    this.#problemRead ??= this.host.context.api
      .get<ProblemDocument>(`/api/v1/problems/${encodeURIComponent(status.slug)}`)
      .then(
        (problem) => {
          this.#problem = problem;
        },
        () => {},
      );
    await this.#problemRead;
    this.toolbar.hidden = false;
    this.buttons.submit.hidden = status.kind !== "project";
    this.buttons.bench.hidden = !(this.#problem?.bench && status.language);
  }

  /** Follows a run another tab started (`run_started`), unless this tab shows one already. */
  attach(runId: string): void {
    void this.#use((session) => session.showLatest(runId, true));
  }

  /** Shows the attempt's newest run the server keeps, live or replayed, unless this tab shows a
   * run already: one that started while the tab could not hear, as while it was hidden. */
  async catchUp(): Promise<void> {
    const runs = await this.host.context.api.get<RunDocument[]>(`/api/v1/runs?attempt_id=${this.host.attemptId}`).catch(() => []);
    const latest = runs[0];
    if (latest?.state === "running") this.attach(latest.id);
  }

  /** Run on save, for a file of the attempt that changed on disk (`file_changed`); the page's
   * own saves are heard as they are made, so their notices start nothing more. */
  fileChanged(path: string, sha256: string | null): void {
    if (this.#ownSaves.delete(savedKey(path, sha256))) return;
    this.#runOnSave();
  }

  /** Stops following the attempt's runs, as once it ended elsewhere. */
  freeze(): void {
    for (const button of [this.buttons.run, this.buttons.submit, this.buttons.options, this.buttons.bench]) button.disabled = true;
    window.clearTimeout(this.#saveTimer);
    this.#frozen = true;
  }

  forgetSaves(): void {
    window.clearTimeout(this.#saveTimer);
  }

  destroy(): void {
    this.#destroyed = true;
    window.clearTimeout(this.#saveTimer);
    void this.#session?.then((session) => session?.destroy());
    this.results.destroy();
    for (const cleanup of this.#cleanups) cleanup();
  }

  runContext(): RunContext {
    const status = this.#status!;
    return {
      slug: status.slug,
      kind: status.kind,
      language: status.language,
      levels: status.levels,
      oracle: this.#problem?.oracle ?? false,
      typecheck: this.host.context.preferences().typecheck,
    };
  }

  /** Each button names the command it runs and its shortcut. */
  showCommands(): void {
    if (this.#status === null) return;
    const context = this.runContext();
    this.buttons.run.title = `${runCommand("test", this.options, context)} (${RUN_KEY})`;
    this.buttons.submit.title = `${runCommand("submit", this.options, context)} (${SUBMIT_KEY})`;
    if (this.#status.language) this.buttons.bench.title = `cstudy bench ${this.#status.slug} --lang ${this.#status.language}`;
  }

  /** The newest run of the attempt still in the server, live or replayed; else what the CLI recorded. */
  async #showLatestRun(status: AttemptStatus): Promise<void> {
    const runs = await this.host.context.api.get<RunDocument[]>(`/api/v1/runs?attempt_id=${this.host.attemptId}`).catch(() => []);
    const latest = runs[0];
    if (latest && (await this.#use((session) => session.showLatest(latest.id, latest.state === "running")))) return;
    this.#showRecorded(status);
  }

  /** The run `cstudy test` last recorded, until the run session shows a run. */
  #showRecorded(status: AttemptStatus): void {
    this.results.show(null, noRunYet(runCommand("test", this.options, this.runContext()), status.last_test_run));
    this.#showsRecorded = true;
  }

  /** Does `act` with the run session, which is fetched the first time; false when it could not be. */
  async #use(act: (session: RunSession) => unknown): Promise<boolean> {
    if (this.#frozen) return false;
    this.#session ??= this.#openSession();
    const session = await this.#session;
    if (session === null || this.#destroyed) return false;
    this.#showsRecorded = false;
    await act(session);
    return true;
  }

  async #openSession(): Promise<RunSession | null> {
    const module = await fetchChunk((message) => this.host.context.shell.announce(message), () => import("./run-session.ts"));
    if (module === null) {
      this.#session = null;
      return null;
    }
    return new module.RunSession(this);
  }

  /** Run on save: a test run 150 ms after a save of the attempt's files. */
  #onSaved(saved: FileSaved): void {
    if (saved.attemptId !== this.host.attemptId) return;
    this.#ownSaves.add(savedKey(saved.path, saved.sha256));
    this.#runOnSave();
  }

  #runOnSave(): void {
    if (!this.host.context.preferences().run_on_save) return;
    window.clearTimeout(this.#saveTimer);
    this.#saveTimer = window.setTimeout(() => void this.#use((session) => session.runOnSave()), RUN_ON_SAVE_DEBOUNCE_MS);
  }

  #onKey(event: KeyboardEvent): void {
    if (event.key !== "Enter" || !(event.metaKey || event.ctrlKey) || event.altKey) return;
    event.preventDefault();
    event.stopPropagation();
    const command: RunCommandName = event.shiftKey ? "submit" : "test";
    void this.#use((session) => session.start(command));
  }

  #listen(target: EventTarget, name: string, listener: (event: Event) => void, capture = false): void {
    target.addEventListener(name, listener, capture);
    this.#cleanups.push(() => target.removeEventListener(name, listener, capture));
  }
}
