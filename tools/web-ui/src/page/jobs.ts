/**
 * A job's panel (docs/specs/web-ui.md#jobs): starts `doctor --fix`, `verify` or `bench` as a child
 * `cstudy`, asks the question a job needs first, and shows its report line by line as it comes,
 * then its exit code. One job runs at a time in the server: a job already running is shown instead.
 */

import { ApiError } from "./api.ts";
import type { PageContext } from "./context.ts";
import { badge, command, h } from "./dom.ts";
import { LiveStream } from "./event-stream.ts";
import type { Closed } from "./run-events.ts";
import { failure } from "./states.ts";

const LINE_EVENT = "line";

interface JobLine {
  readonly stream: "stdout" | "stderr";
  readonly text: string;
}

export interface JobPanelOptions {
  /** Called once the job's child exited. */
  readonly ended?: (closed: Closed) => void;
}

export class JobPanel {
  readonly element: HTMLElement;
  readonly #context: PageContext;
  readonly #options: JobPanelOptions;
  readonly #title: HTMLElement;
  readonly #state: HTMLElement;
  readonly #log: HTMLElement;
  readonly #cancel: HTMLButtonElement;
  #stream: LiveStream | null = null;
  #jobId: string | null = null;

  constructor(context: PageContext, options: JobPanelOptions = {}) {
    this.#context = context;
    this.#options = options;
    this.#title = h("span", { class: "job-title" });
    this.#state = h("span", { class: "job-state", role: "status" });
    this.#cancel = h("button", { type: "button", class: "button job-cancel", disabled: true, title: "Stop the job as Ctrl-C does" }, "■ Cancel");
    this.#cancel.addEventListener("click", () => void this.#cancelJob());
    this.#log = h("pre", { class: "job-log", tabindex: "0", "aria-label": "Job output" });
    this.element = h(
      "section",
      { class: "job", "aria-label": "Job", hidden: true },
      h("header", { class: "job-head" }, h("span", { class: "eyebrow" }, "job"), this.#title, this.#state, h("span", { class: "spacer" }), this.#cancel),
      this.#log,
    );
  }

  get running(): boolean {
    return this.#stream !== null;
  }

  /** Starts the job `body` describes; `shown` is the command it runs, for the panel's title. */
  async start(body: Readonly<Record<string, unknown>>, shown: string): Promise<void> {
    if (this.running) return;
    this.element.hidden = false;
    this.#title.replaceChildren(command(shown));
    this.#state.replaceChildren("starting…");
    this.#log.replaceChildren();
    try {
      const { id } = await this.#context.api.post<{ id: string }>("/api/v1/jobs", body);
      this.#attach(id);
    } catch (error) {
      await this.#refused(error, body, shown);
    }
  }

  destroy(): void {
    this.#stream?.close();
    this.#stream = null;
  }

  async #refused(error: unknown, body: Readonly<Record<string, unknown>>, shown: string): Promise<void> {
    if (error instanceof ApiError && error.code === "confirmation_required") {
      if (window.confirm(error.message)) {
        await this.start({ ...body, confirm: true }, shown);
      } else {
        this.element.hidden = true;
      }
      return;
    }
    const running = error instanceof ApiError ? error.details["job"] : undefined;
    if (typeof running === "string") {
      this.#title.replaceChildren(h("span", { class: "quiet" }, "another job is in progress; it shows here"));
      this.#attach(running);
      return;
    }
    this.#state.replaceChildren();
    this.#log.replaceChildren(failure(error));
  }

  #attach(jobId: string): void {
    this.#jobId = jobId;
    this.#state.replaceChildren(badge("▸", "running", "info"));
    this.#cancel.disabled = false;
    this.#context.shell.announce(`job started: ${this.#title.textContent ?? ""}`);
    this.#stream = new LiveStream(`/api/v1/jobs/${jobId}/events`, [LINE_EVENT], {
      restart: () => this.#log.replaceChildren(),
      message: (_name, data) => this.#append(data as JobLine),
      closed: (closed) => this.#ended(closed),
    });
  }

  #append(line: JobLine): void {
    const atEnd = this.#log.scrollTop + this.#log.clientHeight >= this.#log.scrollHeight - 4;
    this.#log.append(h("span", { class: `job-line job-${line.stream}` }, line.text), "\n");
    if (atEnd) this.#log.scrollTop = this.#log.scrollHeight;
  }

  #ended(closed: Closed): void {
    this.#stream = null;
    this.#cancel.disabled = true;
    const ok = closed.exit_code === 0;
    const text = closed.signal ? `stopped by ${closed.signal}` : `exit ${closed.exit_code}`;
    this.#state.replaceChildren(badge(ok ? "✓" : "✕", text, ok ? "ok" : "fail"));
    this.#context.shell.announce(`job ended: ${text}`);
    this.#options.ended?.(closed);
  }

  async #cancelJob(): Promise<void> {
    if (this.#jobId === null || !this.running) return;
    this.#cancel.disabled = true;
    try {
      await this.#context.api.post(`/api/v1/jobs/${this.#jobId}/cancel`, {});
      this.#state.replaceChildren(badge("▸", "cancelling…", "warn"));
    } catch (error) {
      if (!(error instanceof ApiError && error.code === "conflict")) this.#log.append(failure(error));
    }
  }
}
