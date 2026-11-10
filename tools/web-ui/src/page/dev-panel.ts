/**
 * The dev stack of a service project on the Attempt view (docs/specs/web-ui.md#dev-stack): Start
 * and Stop of `cstudy dev`, the stack's stage, where the app answers on this machine, a scenario
 * picker per mock server, and the app's latest lines. A stack starts only on request, because of its
 * memory, and the tab that started it stops it when it leaves the view or the page, or after five
 * minutes hidden, as a language server's session ends. It is a chunk of its own, fetched with the
 * first service project the view shows.
 */

import "./dev-panel.css";

import { ApiError, CSRF_HEADER } from "./api.ts";
import type { PageContext } from "./context.ts";
import { DEV_EVENT_TYPES, type DevEvent, DevModel } from "./dev-model.ts";
import { badge, command, fixHint, h } from "./dom.ts";
import { LiveStream } from "./event-stream.ts";
import { stackText } from "./results-model.ts";
import { failure } from "./states.ts";
import type { AttemptStatus } from "./types.ts";

const DEVS = "/api/v1/dev";
const HIDDEN_STOP_MS = 5 * 60 * 1000;
const NO_SCENARIO = "";

interface DevDocument {
  readonly id: string;
  readonly state: "running" | "ended";
}

export class DevPanel {
  readonly element: HTMLElement;
  readonly #context: PageContext;
  readonly #status: AttemptStatus;
  readonly #state: HTMLElement;
  readonly #url: HTMLElement;
  readonly #button: HTMLButtonElement;
  readonly #mocks: HTMLElement;
  readonly #log: HTMLElement;
  readonly #note: HTMLElement;
  #model: DevModel;
  #stream: LiveStream | null = null;
  #devId: string | null = null;
  /** Whether this tab started the stack, so leaving stops it. */
  #mine = false;
  #busy = false;
  #hiddenTimer: number | undefined;
  #frame = 0;

  constructor(context: PageContext, status: AttemptStatus) {
    this.#context = context;
    this.#status = status;
    this.#model = new DevModel(status.service?.mocks ?? []);
    this.#state = h("span", { class: "dev-state" });
    this.#url = h("span", { class: "dev-url" });
    this.#button = h("button", { type: "button", class: "button dev-button" });
    this.#button.addEventListener("click", () => void this.#press());
    this.#mocks = h("div", { class: "dev-mocks" });
    this.#log = h("pre", { class: "dev-log", tabindex: "0", "aria-label": "What your app prints" });
    this.#note = h("div", { class: "dev-note", role: "status" });
    this.element = h(
      "section",
      { class: "dev-stack", "aria-label": "Dev stack" },
      h("header", { class: "dev-head" }, h("h2", { class: "eyebrow" }, "dev stack"), this.#state, this.#url, h("span", { class: "spacer" }), this.#button),
      this.#mocks,
      this.#note,
      this.#log,
    );
    document.addEventListener("visibilitychange", this.#onVisibility);
    window.addEventListener("pagehide", this.#onPageHide);
    this.#draw();
    void this.#catchUp();
  }

  destroy(): void {
    document.removeEventListener("visibilitychange", this.#onVisibility);
    window.removeEventListener("pagehide", this.#onPageHide);
    window.clearTimeout(this.#hiddenTimer);
    cancelAnimationFrame(this.#frame);
    if (this.#mine && this.#running) void this.#context.api.post(`${DEVS}/${this.#devId}/stop`, {}).catch(() => {});
    this.#stream?.close();
  }

  get #running(): boolean {
    return this.#devId !== null && this.#model.phase !== "ended";
  }

  /** A stack this attempt has already, started by another tab or before a reload. */
  async #catchUp(): Promise<void> {
    const devs = await this.#context.api.get<DevDocument[]>(`${DEVS}?attempt_id=${this.#status.attempt_id}`).catch(() => []);
    const latest = devs[0];
    if (latest?.state === "running" && this.#devId === null) this.#follow(latest.id, false);
  }

  async #press(): Promise<void> {
    if (this.#busy) return;
    if (this.#running) await this.#stop();
    else await this.#start();
  }

  async #start(): Promise<void> {
    this.#busy = true;
    this.#note.replaceChildren();
    try {
      const { id } = await this.#context.api.post<{ id: string }>(DEVS, { attempt_id: this.#status.attempt_id });
      this.#follow(id, true);
      this.#context.shell.announce(`starting cstudy dev ${this.#status.slug}; the same button now stops it`);
    } catch (error) {
      const held = error instanceof ApiError && error.code === "conflict" ? error.details["dev"] : undefined;
      if (typeof held === "string") this.#follow(held, false);
      else this.#note.replaceChildren(failure(error));
    } finally {
      this.#busy = false;
      this.#draw();
    }
  }

  async #stop(): Promise<void> {
    this.#busy = true;
    this.#draw();
    try {
      await this.#context.api.post(`${DEVS}/${this.#devId}/stop`, {});
      this.#context.shell.announce("stopping the dev stack");
    } catch (error) {
      if (!(error instanceof ApiError && error.code === "conflict")) this.#note.replaceChildren(failure(error));
    } finally {
      this.#busy = false;
    }
  }

  #follow(devId: string, mine: boolean): void {
    this.#stream?.close();
    this.#devId = devId;
    this.#mine = mine;
    this.#model = new DevModel(this.#status.service?.mocks ?? []);
    this.#model.phase = "starting";
    this.#stream = new LiveStream(`${DEVS}/${devId}/events`, DEV_EVENT_TYPES, {
      restart: () => {
        this.#model = new DevModel(this.#status.service?.mocks ?? []);
        this.#update();
      },
      message: (_name, data) => {
        this.#model.apply(data as DevEvent);
        this.#update();
      },
      closed: (closed) => {
        this.#stream = null;
        this.#model.close(closed);
        this.#update();
      },
      lost: () => {
        this.#stream = null;
        this.#model.close({ exit_code: 0, signal: null, stderr: ["The server no longer keeps this dev stack, as after a restart."] });
        this.#update();
      },
    });
    this.#draw();
  }

  async #switch(mock: string, scenario: string | null): Promise<void> {
    if (this.#devId === null) return;
    try {
      await this.#context.api.post(`${DEVS}/${this.#devId}/scenario`, { mock, scenario });
    } catch (error) {
      this.#note.replaceChildren(failure(error));
    }
  }

  /** Draws again on the next frame, so a burst of app lines costs one layout. */
  #update(): void {
    if (this.#frame) return;
    this.#frame = requestAnimationFrame(() => {
      this.#frame = 0;
      this.#draw();
    });
  }

  #draw(): void {
    const model = this.#model;
    const running = this.#running;
    this.element.dataset["phase"] = this.#devId === null ? "idle" : model.phase;
    this.#state.replaceChildren(this.#stateBadge());
    this.#url.replaceChildren(...(model.appUrl ? [h("a", { href: model.appUrl, target: "_blank", rel: "noopener noreferrer", class: "dev-app-link" }, model.appUrl, h("span", { "aria-hidden": "true" }, " ↗"))] : []));
    this.#button.textContent = running ? "Stop" : "Start dev stack";
    this.#button.classList.toggle("primary", !running);
    this.#button.disabled = this.#busy;
    this.#button.title = running ? "Stop the stack as Ctrl-C does; its data stays" : `cstudy dev ${this.#status.slug}`;
    this.#mocks.replaceChildren(...model.mocks.map((mock) => this.#picker(mock.name, mock.scenario, mock.scenarios, model.phase === "ready")));
    this.#drawNote();
    const following = this.#log.scrollTop + this.#log.clientHeight >= this.#log.scrollHeight - 8;
    this.#log.textContent = model.lines.join("\n");
    this.#log.hidden = model.lines.length === 0;
    if (following) this.#log.scrollTop = this.#log.scrollHeight;
  }

  #stateBadge(): HTMLElement {
    const model = this.#model;
    if (this.#devId === null || (model.phase === "ended" && model.stack === null)) {
      return h("span", { class: "quiet" }, model.phase === "ended" ? "ended" : "not running · ", model.phase === "ended" ? null : command(`cstudy dev ${this.#status.slug}`));
    }
    if (model.stack === null) return badge("▸", "starting", "info");
    const tone = model.stack.state === "ready" ? "ok" : model.stack.state === "failed" ? "fail" : model.stack.down ? "quiet" : "info";
    const glyph = model.stack.state === "ready" ? "●" : model.stack.state === "failed" ? "✕" : model.stack.down ? "■" : "▸";
    return badge(glyph, stackText(model.stack), tone);
  }

  #drawNote(): void {
    const { refusal, end } = this.#model;
    if (refusal) {
      this.#note.replaceChildren(h("p", { class: "tone-warn" }, refusal));
      return;
    }
    if (end?.message && this.#model.phase === "ended") {
      this.#note.replaceChildren(h("p", { class: "dev-end" }, fixHint(end.message)), ...(end.output ? [h("pre", { class: "dev-output" }, end.output)] : []));
      return;
    }
    if (this.#devId === null) this.#note.replaceChildren(h("p", { class: "quiet" }, "Runs your app and its mock servers until you stop it or leave the page; nothing is graded."));
  }

  #picker(mock: string, scenario: string | null, scenarios: readonly string[], live: boolean): HTMLElement {
    const id = `dev-scenario-${mock}`;
    const select = h(
      "select",
      { id, disabled: !live },
      h("option", { value: NO_SCENARIO, selected: scenario === null }, "no scenario"),
      ...scenarios.map((name) => h("option", { value: name, selected: name === scenario }, name)),
    );
    select.addEventListener("change", () => void this.#switch(mock, select.value === NO_SCENARIO ? null : select.value));
    return h("div", { class: "dev-mock" }, h("label", { for: id }, mock), select);
  }

  /** A hidden tab stops a stack it started after five minutes, as it closes its sessions. */
  readonly #onVisibility = (): void => {
    window.clearTimeout(this.#hiddenTimer);
    if (!document.hidden || !this.#mine) return;
    this.#hiddenTimer = window.setTimeout(() => {
      if (this.#mine && this.#running) void this.#stop();
    }, HIDDEN_STOP_MS);
  };

  /** Leaving the page stops a stack this tab started: a request that outlives the page. */
  readonly #onPageHide = (): void => {
    if (!this.#mine || !this.#running) return;
    void fetch(`${DEVS}/${this.#devId}/stop`, {
      method: "POST",
      keepalive: true,
      headers: { "Content-Type": "application/json", [CSRF_HEADER]: this.#context.csrf },
      body: "{}",
    }).catch(() => {});
  };
}
