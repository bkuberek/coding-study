/**
 * What an Attempt view does with a run (docs/specs/web-ui.md#runs): starts it, follows its stream
 * into the results panel, cancels it through the button that started it, marks its diagnostics in the editors, starts Bench as a job,
 * and runs again after a save that came during a run. It is a chunk of its own, with the run's
 * model and drawing, fetched the first time a run starts or shows (`AttemptRuns` in `runs.ts`), so
 * the page loads less before a file is editable (NFR-12).
 */

import { ApiError } from "./api.ts";
import type { Confirmation } from "./dialogs.ts";
import { h } from "./dom.ts";
import { LiveStream } from "./event-stream.ts";
import { confirmLazily, fetchChunk } from "./lazy.ts";
import type { JobPanel } from "./jobs.ts";
import { drawRun } from "./results-draw.ts";
import { resultsView, RunModel } from "./results-model.ts";
import { diagnosticPath, diagnosticsByPath } from "./run-diagnostics.ts";
import { type Diagnostic, RUN_EVENT_TYPES, type RunEvent } from "./run-events.ts";
import type { RunOptionsForm } from "./run-options-form.ts";
import { type RunCommandName, runBody, runCommand, type RunOptionsState } from "./run-options.ts";
import type { RunShell } from "./runs.ts";
import { failure } from "./states.ts";

const CANCEL_TITLE = "Stop the run as Ctrl-C does; asks first (Escape in the results too)";
const CANCEL_QUESTION: Confirmation = {
  title: "Cancel the run?",
  message: "cstudy stops it as Ctrl-C does and records nothing.",
  action: "Cancel the run",
  dismiss: "Keep it running",
  destructive: true,
};

export class RunSession {
  readonly #shell: RunShell;
  readonly #cleanups: (() => void)[] = [];
  #form: RunOptionsForm | null = null;
  #bench: JobPanel | null = null;
  #model: RunModel | null = null;
  #stream: LiveStream | null = null;
  #runId: string | null = null;
  #starting = false;
  /** The command whose button cancels the run in progress: the one that started it, else Run tests. */
  #active: RunCommandName | null = null;
  #cancelling = false;
  #queued = false;
  #refreshOnUnlock = false;
  #byPath = new Map<string, Diagnostic[]>();
  #destroyed = false;

  constructor(shell: RunShell) {
    this.#shell = shell;
    shell.results.bind(drawRun, {
      jumpTarget: (diagnostic) => this.#jumpTarget(diagnostic),
      rerun: (id, seed) => void this.start("test", { cases: [id], stress: 1, seed }),
    });
    const onKey = (event: KeyboardEvent) => this.#onResultsKey(event);
    shell.results.body.addEventListener("keydown", onKey);
    this.#cleanups.push(() => shell.results.body.removeEventListener("keydown", onKey));
    this.#cleanups.push(shell.host.tabs.onEditor((path, editor) => editor.setDiagnostics(this.#byPath.get(path) ?? [])));
  }

  readonly #announce = (message: string): void => this.#shell.host.context.shell.announce(message);

  get #running(): boolean {
    return this.#starting || this.#stream !== null;
  }

  destroy(): void {
    this.#destroyed = true;
    this.#stream?.close();
    this.#bench?.destroy();
    for (const cleanup of this.#cleanups) cleanup();
  }

  /** Draws the form again, as after a level opened. */
  configure(): void {
    this.#form?.configure(this.#shell.runContext(), this.#shell.options);
  }

  /** Shows the run the server still keeps for the attempt, live or replayed, unless one started meanwhile. */
  showLatest(runId: string, live: boolean): void {
    if (!this.#running) this.#attach(runId, live);
  }

  /** Run on save: a test run, or one more after the run in progress. A run still starting sees the save. */
  runOnSave(): void {
    if (this.#starting) return;
    if (this.#running) this.#queued = true;
    else void this.start("test");
  }

  /**
   * A run tests what the editors show: every tab's edits are saved first, through the save the
   * shortcut uses. When one can't be, or a tab has a conflict with the file on disk, no run starts:
   * its banner offers the way on, and the results say which file and why.
   */
  async #savedForRun(): Promise<boolean> {
    const problems = await this.#shell.host.tabs.saveForRun();
    this.#shell.forgetSaves();
    if (problems.length === 0) return true;
    const refusal = `not run: ${problems.join("; ")}. Settle it in its tab, then run again`;
    this.#shell.results.show(null, [failure(new Error(refusal))]);
    this.#announce(refusal);
    return false;
  }

  async start(command: RunCommandName, change: Partial<RunOptionsState> = {}): Promise<void> {
    const { status } = this.#shell;
    if (this.#running || status === null || status.kind === "item") return;
    if (command === "submit" && status.kind !== "project") return;
    const options = { ...this.#shell.options, ...change };
    const context = this.#shell.runContext();
    this.#starting = true;
    this.#active = command;
    this.#showState();
    try {
      if (!(await this.#savedForRun())) return;
      const { id } = await this.#shell.host.context.api.post<{ id: string }>("/api/v1/runs", runBody(this.#shell.host.attemptId, command, options, context));
      this.#announce(`running ${runCommand(command, options, context)}; the same button now cancels it`);
      this.#attach(id, true);
    } catch (error) {
      const active = error instanceof ApiError && error.code === "conflict" ? error.details["run"] : undefined;
      if (typeof active === "string") {
        this.#active = null;
        this.#attach(active, true);
        return;
      }
      this.#shell.results.show(null, [failure(error)]);
    } finally {
      this.#starting = false;
      if (this.#stream === null) this.#active = null;
      this.#showState();
    }
  }

  /** What Run tests and Submit do when pressed: the one whose run is active cancels it. */
  press(command: RunCommandName): Promise<void> {
    return this.#stream !== null && this.#active === command ? this.cancel() : this.start(command);
  }

  /** Stops the run in progress, after the question Escape in the results asks too. */
  async cancel(): Promise<void> {
    if (this.#runId === null || this.#stream === null || this.#cancelling) return;
    if (!(await confirmLazily(CANCEL_QUESTION)) || this.#stream === null) return;
    this.#cancelling = true;
    try {
      await this.#shell.host.context.api.post(`/api/v1/runs/${this.#runId}/cancel`, {});
      this.#announce("cancelling the run");
    } catch (error) {
      this.#cancelling = false;
      if (!(error instanceof ApiError && error.code === "conflict")) this.#shell.results.show(this.#model, [failure(error)]);
    }
  }

  async flipOptions(): Promise<void> {
    const form = await this.#optionsForm();
    if (form === null) return;
    const open = form.element.hidden;
    form.element.hidden = !open;
    this.#shell.buttons.options.setAttribute("aria-expanded", String(open));
  }

  async startBench(): Promise<void> {
    const status = this.#shell.status;
    if (!status?.language || !(await this.#savedForRun())) return;
    const bench = await this.#benchPanel();
    await bench?.start({ command: "bench", slug: status.slug, language: status.language }, `cstudy bench ${status.slug} --lang ${status.language}`);
  }

  /** Shows the run and follows its stream. */
  #attach(runId: string, live: boolean): void {
    if (this.#destroyed) return;
    const { results } = this.#shell;
    this.#stream?.close();
    this.#runId = runId;
    this.#active ??= "test";
    this.#refreshOnUnlock = live;
    this.#model = new RunModel();
    results.show(this.#model);
    this.#stream = new LiveStream(`/api/v1/runs/${runId}/events`, RUN_EVENT_TYPES, {
      restart: () => {
        this.#model = new RunModel();
        results.show(this.#model);
      },
      message: (_name, data) => this.#onEvent(data as RunEvent),
      closed: (closed) => {
        this.#stopped();
        this.#model?.close(closed);
        results.update();
        this.#ended();
      },
      lost: () => {
        this.#stopped();
        results.show(null, [h("p", { class: "quiet" }, "The server no longer keeps this run, as after a restart; run the tests again.")]);
        this.#showState();
      },
    });
    this.#showState();
  }

  /** The stream of the run ended: nothing is left to cancel. */
  #stopped(): void {
    this.#stream = null;
    this.#active = null;
    this.#cancelling = false;
  }

  #onEvent(event: RunEvent): void {
    const model = this.#model;
    if (!model) return;
    model.apply(event);
    this.#shell.results.update();
    if (event.type === "run_start") this.#markDiagnostics([]);
    if (event.type === "diagnostic") this.#markDiagnostics(model.diagnostics);
  }

  #ended(): void {
    this.#showState();
    const model = this.#model;
    if (model) {
      const summary = resultsView(model, false).summary;
      this.#announce(summary ? `run ended: ${summary.text}` : "run ended");
      if (model.unlocked && this.#refreshOnUnlock) this.#shell.host.refresh();
    }
    if (this.#queued) {
      this.#queued = false;
      void this.start("test");
    }
  }

  /** The job panel for Bench, fetched with its code the first time Bench starts. */
  async #benchPanel(): Promise<JobPanel | null> {
    const module = this.#bench === null ? await fetchChunk(this.#announce, () => import("./jobs.ts")) : null;
    if (this.#bench === null && module !== null && !this.#destroyed) {
      this.#bench = new module.JobPanel(this.#shell.host.context);
      this.#shell.results.addJob(this.#bench.element);
    }
    return this.#bench;
  }

  /** The Run options form, fetched with its code the first time it opens. */
  async #optionsForm(): Promise<RunOptionsForm | null> {
    const module = this.#form === null ? await fetchChunk(this.#announce, () => import("./run-options-form.ts")) : null;
    if (this.#form === null && module !== null && !this.#destroyed) {
      const form = new module.RunOptionsForm(this.#shell.options, (options) => {
        this.#shell.options = options;
        this.#shell.showCommands();
      });
      form.element.id = "run-options";
      this.#shell.buttons.options.setAttribute("aria-controls", "run-options");
      this.#shell.results.addOptions(form.element);
      form.configure(this.#shell.runContext(), this.#shell.options);
      this.#form = form;
    }
    return this.#form;
  }

  /** Replaces every editor's markers with the run's diagnostics of its file. */
  #markDiagnostics(diagnostics: readonly Diagnostic[]): void {
    this.#byPath = diagnosticsByPath(diagnostics, this.#shell.status?.kind ?? "", this.#shell.root);
    for (const [path, editor] of this.#shell.host.tabs.editors()) editor.setDiagnostics(this.#byPath.get(path) ?? []);
  }

  #jumpTarget(diagnostic: Diagnostic): (() => void) | null {
    const path = diagnosticPath(diagnostic.file, this.#shell.status?.kind ?? "", this.#shell.root);
    if (path === null || !this.#shell.host.hasFile(path)) return null;
    return () => {
      const tabs = this.#shell.host.tabs;
      void tabs.open(path).then(() => tabs.editors().get(path)?.jumpTo(diagnostic.line ?? 1, diagnostic.column));
    };
  }

  #onResultsKey(event: KeyboardEvent): void {
    if (event.key !== "Escape" || this.#stream === null) return;
    event.preventDefault();
    void this.cancel();
  }

  /** Run tests and Submit: the one whose run is active reads Cancel, in its own place, and keeps
   * the focus; the other waits disabled. A run still starting disables only the other, since a
   * disabled button loses the focus. */
  #showState(): void {
    const { buttons, toolbar } = this.#shell;
    this.#shell.showCommands();
    for (const [command, button] of [["test", buttons.run], ["submit", buttons.submit]] as const) {
      const cancels = this.#stream !== null && this.#active === command;
      button.classList.toggle("is-cancel", cancels);
      button.disabled = this.#running && this.#active !== command;
      if (cancels) button.title = CANCEL_TITLE;
    }
    toolbar.classList.toggle("is-running", this.#running);
  }
}
