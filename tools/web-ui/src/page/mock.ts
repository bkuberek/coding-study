/**
 * Mock interviews (docs/specs/web-ui.md#mock-view): the state of the mock that runs, wherever it
 * started, which the top bar's banner, the Mock view and the Hint and Solution buttons follow.
 */

import { ApiError, type Api } from "./api.ts";
import { h } from "./dom.ts";
import type { NotificationStream } from "./notifications.ts";
import { MOCK_HASH } from "./routes.ts";
import type { MockAttempt, MockState, StartedMock } from "./types.ts";

const SECONDS_PER_MINUTE = 60;
const TICK_MS = 1000;

/** What the watch uses of the notification stream. */
export type NoticeSource = Pick<NotificationStream, "subscribe">;
/** `cstudy mock`'s defaults. */
export const DEFAULT_MINUTES = 45;
export const DEFAULT_COUNT = 2;

export interface MockForm {
  readonly minutes: number;
  readonly count: number;
  /** Empty: the configuration's `next.tracks`. */
  readonly tracks: readonly string[];
  /** Null: `default_lang`. */
  readonly language: string | null;
}

export interface MockCard extends MockAttempt {
  /** `finished` once the attempt left the mock and is no longer in progress. */
  readonly status: "in_progress" | "finished";
}

/** `31:20`: minutes and seconds left, as the lock message writes them. */
export function countdown(seconds: number): string {
  const left = Math.max(Math.floor(seconds), 0);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${pad(Math.floor(left / SECONDS_PER_MINUTE))}:${pad(left % SECONDS_PER_MINUTE)}`;
}

export function bannerText(remaining: number): string {
  return `Mock interview · ${countdown(remaining)} left · hints and solutions locked`;
}

/** The message the server refuses `command` with during the mock. */
export function lockMessage(command: string, slugs: readonly string[], remaining: number): string {
  const unfinished = [...slugs].sort().join(", ");
  return `${command} is locked during the mock interview (${unfinished}; ${countdown(remaining)} left); it unlocks when the timer ends or every problem is done`;
}

export function mockCommand(form: MockForm): string {
  const flags = [
    form.minutes === DEFAULT_MINUTES ? null : `--minutes ${form.minutes}`,
    form.count === DEFAULT_COUNT ? null : `--count ${form.count}`,
    ...form.tracks.map((track) => `--track ${track}`),
    form.language === null ? null : `--lang ${form.language}`,
  ];
  return ["cstudy mock", ...flags].filter(Boolean).join(" ");
}

/**
 * The mock that runs, read from `GET /api/v1/mock`, and a card for every attempt this tab has
 * seen in it: the server lists only the unfinished ones, so a card that left the list is checked
 * once and shows `finished` when its attempt ended.
 */
export class MockWatch {
  readonly #api: Api;
  readonly #now: () => number;
  readonly #listeners = new Set<(state: MockState) => void>();
  readonly #cards = new Map<number, MockCard>();
  #state: MockState | null = null;
  #readAt = 0;

  constructor(api: Api, now: () => number = () => Date.now()) {
    this.#api = api;
    this.#now = now;
  }

  state(): MockState | null {
    return this.#state;
  }

  /** Seconds left on the shared timer, counted from when it was read; 0 when none runs. */
  remaining(): number {
    const state = this.#state;
    if (!state?.running) return 0;
    return Math.max(state.remaining_s - (this.#now() - this.#readAt) / 1000, 0);
  }

  cards(): MockCard[] {
    return [...this.#cards.values()];
  }

  /** The lock message for `command`, or null when no mock runs. */
  lock(command: string): string | null {
    const state = this.#state;
    if (!state?.running) return null;
    return lockMessage(command, state.attempts.map((attempt) => attempt.slug), this.remaining());
  }

  subscribe(listener: (state: MockState) => void): () => void {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }

  /** Calls `apply` with `command`'s lock message now and after each read, until `element`, put
   * on the page right after this call, has left it. */
  follow(command: string, element: Element, apply: (lock: string | null) => void): void {
    apply(this.lock(command));
    const unsubscribe = this.subscribe(() => {
      if (element.isConnected) apply(this.lock(command));
      else unsubscribe();
    });
  }

  async refresh(): Promise<MockState> {
    const state = await this.#api.get<MockState>("/api/v1/mock");
    this.#readAt = this.#now();
    const listed = new Set(state.running ? state.attempts.map((attempt) => attempt.attempt_id) : []);
    if (state.running && ![...listed].some((id) => this.#cards.has(id))) this.#cards.clear();
    if (state.running) for (const attempt of state.attempts) this.#cards.set(attempt.attempt_id, { ...attempt, status: "in_progress" });
    const left = this.cards().filter((card) => card.status === "in_progress" && !listed.has(card.attempt_id));
    await Promise.all(left.map((card) => this.#check(card)));
    this.#state = state;
    for (const listener of this.#listeners) listener(state);
    return state;
  }

  /** A mock this tab started: its problems become the cards. */
  async started(mock: StartedMock): Promise<void> {
    this.#cards.clear();
    for (const problem of mock.problems) this.#cards.set(problem.attempt_id, { ...problem, status: "in_progress" });
    await this.refresh();
  }

  /** Reads the state now, after each `progress_changed` of the notification stream (a mock is
   * nothing but its attempts) and each time the stream opens again, and when the countdown reaches
   * zero; the function returned stops. */
  watch(notices: NoticeSource): () => void {
    let deadline: ReturnType<typeof setTimeout> | undefined;
    const read = () => {
      void this.refresh()
        .then((state) => {
          clearTimeout(deadline);
          if (state.running) deadline = setTimeout(read, state.remaining_s * 1000 + TICK_MS);
        })
        .catch(() => {});
    };
    read();
    const unsubscribe = notices.subscribe((notice) => {
      if (notice.type === "progress_changed" || notice.type === "resync") read();
    });
    return () => {
      unsubscribe();
      clearTimeout(deadline);
    };
  }

  async #check(card: MockCard): Promise<void> {
    try {
      await this.#api.get(`/api/v1/attempts/${card.attempt_id}`);
    } catch (error) {
      if (error instanceof ApiError) this.#cards.set(card.attempt_id, { ...card, status: "finished" });
    }
  }
}

/** The top bar's banner, shown while a mock runs and linking to the Mock view. */
export function mockBanner(watch: MockWatch): HTMLElement {
  const banner = h("a", { href: MOCK_HASH, class: "mock-banner", hidden: true });
  const tick = () => {
    const running = watch.state()?.running === true;
    banner.hidden = !running;
    if (running) banner.textContent = bannerText(watch.remaining());
  };
  watch.subscribe(tick);
  window.setInterval(tick, TICK_MS);
  return banner;
}

