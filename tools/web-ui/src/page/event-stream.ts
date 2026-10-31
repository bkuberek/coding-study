/**
 * A run's or a job's stream of server-sent events (docs/specs/web-ui.md#server-sent-events). It
 * closes while the tab is hidden, as every stream of the page does, and opens again from the start
 * once the tab shows: a new `EventSource` cannot send `Last-Event-ID`, so the listener starts over
 * and the replay redraws it. The server's `closed` ends the stream for good.
 */

import type { Closed } from "./run-events.ts";

export const CLOSED_EVENT = "closed";

export interface StreamListener {
  /** The stream opens again from its first message: forget what it said so far. */
  restart(): void;
  message(event: string, data: unknown): void;
  closed(closed: Closed): void;
}

export class LiveStream {
  readonly #url: string;
  readonly #events: readonly string[];
  readonly #listener: StreamListener;
  #source: EventSource | null = null;
  #opened = false;
  #ended = false;

  constructor(url: string, events: readonly string[], listener: StreamListener) {
    this.#url = url;
    this.#events = events;
    this.#listener = listener;
    document.addEventListener("visibilitychange", this.#onVisibility);
    if (!document.hidden) this.#open();
  }

  /** Stops listening; the run or job goes on in the server. */
  close(): void {
    this.#ended = true;
    this.#source?.close();
    this.#source = null;
    document.removeEventListener("visibilitychange", this.#onVisibility);
  }

  #open(): void {
    if (this.#opened) this.#listener.restart();
    this.#opened = true;
    const source = new EventSource(this.#url);
    for (const name of this.#events) {
      source.addEventListener(name, (event) => this.#listener.message(name, JSON.parse((event as MessageEvent<string>).data)));
    }
    source.addEventListener(CLOSED_EVENT, (event) => {
      this.close();
      this.#listener.closed(JSON.parse((event as MessageEvent<string>).data) as Closed);
    });
    this.#source = source;
  }

  readonly #onVisibility = (): void => {
    if (this.#ended) return;
    if (document.hidden) {
      this.#source?.close();
      this.#source = null;
    } else if (this.#source === null) {
      this.#open();
    }
  };
}
