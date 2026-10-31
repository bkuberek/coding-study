/**
 * What an Attempt view does with a run (docs/specs/web-ui.md#runs): starts it, follows its stream
 * into the results panel, cancels it, marks its diagnostics in the editors, starts Bench as a job,
 * and runs again after a save that came during a run. It is a chunk of its own, with the run's
 * model and drawing, fetched the first time a run starts or shows (`AttemptRuns` in `runs.ts`), so
 * the page loads less before a file is editable (NFR-12).
 */

import { ApiError } from "./api.ts";
import { h } from "./dom.ts";
import { LiveStream } from "./event-stream.ts";
import { fetchChunk } from "./lazy.ts";
import type { JobPanel } from "./jobs.ts";
import { drawRun } from "./results-draw.ts";
import { resultsView, RunModel } from "./results-model.ts";
import { diagnosticPath, diagnosticsByPath } from "./run-diagnostics.ts";
import { type Diagnostic, RUN_EVENT_TYPES, type RunEvent } from "./run-events.ts";
import type { RunOptionsForm } from "./run-options-form.ts";
import { type RunCommandName, runBody, runCommand, type RunOptionsState } from "./run-options.ts";
import type { RunShell } from "./runs.ts";
import { failure } from "./states.ts";

const CANCEL_QUESTION = "Cancel the run? cstudy stops it as Ctrl-C does and records nothing.";

export class RunSession {
  readonly #shell: RunShell;
  readonly #cleanups: (() => void)[] = [];
  #form: RunOptionsForm | null = null;
  #bench: JobPanel | null = null;
  #model: RunModel | null = null;
  #stream: LiveStream | null = null;
  #runId: string | null = null;
  #starting = false;
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

  /** Run on save: a test run, or one more after the run in progress. */
  runOnSave(): void {
    if (this.#running) this.#queued = true;
    else void this.start("test");
  }

  async start(command: RunCommandName, change: Partial<RunOptionsState> = {}): Promise<void> {
    const { status } = this.#shell;
    if (this.#running || status === null || status.kind === "item") return;
    if (command === "submit" && status.kind !== "project") return;
    const options = { ...this.#shell.options, ...change };
    const context = this.#shell.runContext();
    this.#starting = true;
    this.#showState();
    try {
      const { id } = await this.#shell.host.context.api.post<{ id: string }>("/api/v1/runs", runBody(this.#shell.host.attemptId, command, options, context));
      this.#shell.host.context.shell.announce(`running ${runCommand(command, options, context)}`);
      this.#attach(id, true);
    } catch (error) {
      const active = error instanceof ApiError && error.code === "conflict" ? error.details["run"] : undefined;
      if (typeof active === "string") {
        this.#attach(active, true);
        return;
      }
      this.#shell.results.show(null, [failure(error)]);
    } finally {
      this.#starting = false;
      this.#showState();
    }
  }

  async cancel(): Promise<void> {
    if (this.#runId === null || this.#stream === null) return;
    this.#shell.buttons.cancel.disabled = true;
    try {
      await this.#shell.host.context.api.post(`/api/v1/runs/${this.#runId}/cancel`, {});
      this.#shell.host.context.shell.announce("cancelling the run");
    } catch (error) {
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
    if (!status?.language) return;
    const bench = await this.#benchPanel();
    await bench?.start({ command: "bench", slug: status.slug, language: status.language }, `cstudy bench ${status.slug} --lang ${status.language}`);
  }

  /** Shows the run and follows its stream. */
  #attach(runId: string, live: boolean): void {
    if (this.#destroyed) return;
    const { results } = this.#shell;
    this.#stream?.close();
    this.#runId = runId;
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
        this.#stream = null;
        this.#model?.close(closed);
        results.update();
        this.#ended();
      },
      lost: () => {
        this.#stream = null;
        results.show(null, [h("p", { class: "quiet" }, "The server no longer keeps this run, as after a restart; run the tests again.")]);
        this.#showState();
      },
    });
    this.#showState();
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
      this.#shell.host.context.shell.announce(summary ? `run ended: ${summary.text}` : "run ended");
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
    if (window.confirm(CANCEL_QUESTION)) void this.cancel();
  }

  #showState(): void {
    const running = this.#running;
    const { buttons, toolbar } = this.#shell;
    buttons.run.disabled = running;
    buttons.submit.disabled = running;
    buttons.cancel.disabled = this.#stream === null;
    toolbar.classList.toggle("is-running", running);
  }
}
