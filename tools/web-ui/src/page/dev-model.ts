/**
 * A dev stack as its `cstudy dev --events` stream tells it (docs/specs/web-ui.md#dev-stack): the
 * stack's stage, where the app answers, what each mock server holds, the app's latest lines and how
 * it ended. Pure, so a replayed stream draws the same panel as a live one.
 */

import { type StackStanding, stackStanding } from "./results-model.ts";
import type { Closed, Output } from "./run-events.ts";
import type { MockScenarios } from "./types.ts";

/** The app lines a panel keeps; the stream itself keeps them all. */
export const MAX_APP_LINES = 200;

export interface MockState {
  readonly name: string;
  /** The scenario it holds; null for none. */
  readonly scenario: string | null;
  /** Its visible scenarios, which the stack may switch it to. */
  readonly scenarios: readonly string[];
}

export interface DevReady {
  readonly type: "dev_ready";
  readonly app_url: string;
  readonly startup_s: number;
  readonly mocks: readonly MockState[];
}

export interface AppLine {
  readonly type: "app";
  readonly text: string;
}

export interface ScenarioSwitched {
  readonly type: "scenario";
  readonly mock: string | null;
  readonly scenario: string | null;
  /** Why the switch was refused; null when it was made. */
  readonly message: string | null;
}

export interface DevEnd {
  readonly type: "dev_end";
  readonly outcome: "stopped" | "app_exited" | "load_failed" | "error";
  readonly exit_code: number;
  readonly message: string | null;
  readonly output?: string;
}

export type DevEvent = Output | DevReady | AppLine | ScenarioSwitched | DevEnd;

export const DEV_EVENT_TYPES: readonly DevEvent["type"][] = ["output", "dev_ready", "app", "scenario", "dev_end"];

export type DevPhase = "idle" | "starting" | "ready" | "ended";

/** What the panel's one button does: start a stack, stop the one it follows, or wait while that one comes down. */
export type DevPress = "start" | "stop" | "wait";

export class DevModel {
  phase: DevPhase = "idle";
  /** The stream closed: `cstudy dev` exited, and the server holds its stack no more. */
  exited = false;
  stack: StackStanding | null = null;
  appUrl: string | null = null;
  mocks: MockState[];
  readonly lines: string[] = [];
  refusal: string | null = null;
  end: { readonly message: string | null; readonly output: string | null } | null = null;

  constructor(mocks: readonly MockScenarios[]) {
    this.mocks = mocks.map((mock) => ({ name: mock.name, scenario: null, scenarios: mock.scenarios }));
  }

  apply(event: DevEvent): void {
    switch (event.type) {
      case "output":
        if (this.phase === "idle") this.phase = "starting";
        if (event.stack) this.stack = stackStanding(this.stack, event.stack, event.startup_s);
        return;
      case "dev_ready":
        this.phase = "ready";
        this.appUrl = event.app_url;
        this.mocks = [...event.mocks];
        return;
      case "app":
        this.lines.push(event.text);
        if (this.lines.length > MAX_APP_LINES) this.lines.splice(0, this.lines.length - MAX_APP_LINES);
        return;
      case "scenario":
        this.refusal = event.message;
        this.mocks = this.mocks.map((mock) => (mock.name === event.mock ? { ...mock, scenario: event.scenario } : mock));
        return;
      case "dev_end":
        this.#ended(event.message, event.output ?? null);
    }
  }

  /** The server's last message: the child exited, with or without its own end. */
  close(closed: Closed): void {
    this.exited = true;
    if (this.end === null) this.#ended(closed.stderr.join("\n") || `cstudy dev exited ${closed.exit_code}`, null);
  }

  #ended(message: string | null, output: string | null): void {
    this.phase = "ended";
    this.appUrl = null;
    this.end = { message, output };
  }
}

/**
 * What the button does for the stack the panel follows, if any. One that is down, or whose `dev_end`
 * came, has nothing left to stop, yet the server holds the attempt's dev stack until `cstudy dev`
 * exits: a start before then is refused and attaches to the stack coming down, so the button waits.
 */
export function devPress(following: boolean, model: DevModel): DevPress {
  if (!following || model.exited) return "start";
  return model.phase === "ended" || model.stack?.down === true ? "wait" : "stop";
}
