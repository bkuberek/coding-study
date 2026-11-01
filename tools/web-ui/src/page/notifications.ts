/**
 * The tab's notification stream (docs/specs/web-ui.md#notifications): what changed elsewhere, in
 * another tab, the terminal or an editor, for the views to follow. A tab holds one stream, and
 * closes it while it is hidden, as it does a run's. The browser's own reconnects send
 * `Last-Event-ID`, so the server replays what the stream missed; a stream the page opens again,
 * after the tab was hidden or the stream was refused, cannot, so the views hear `resync` instead
 * and read again what they show. They hear it after a reconnect too, as a server keeps only so
 * many notices.
 */

export const EVENTS_URL = "/api/v1/events";

export interface FileChanged {
  readonly type: "file_changed";
  readonly attempt_id: number;
  /** Relative to the attempt's root. */
  readonly path: string;
  /** Of the file now; null once it is gone. */
  readonly sha256: string | null;
}

export interface AttemptChanged {
  readonly type: "attempt_changed";
  readonly attempt_id: number;
  readonly slug: string;
}

export interface ProgressChanged {
  readonly type: "progress_changed";
}

export interface RunStarted {
  readonly type: "run_started";
  readonly run_id: string;
  readonly attempt_id: number;
  readonly command: string;
}

export interface RunEnded {
  readonly type: "run_ended";
  readonly run_id: string;
  readonly attempt_id: number;
  readonly command: string;
  readonly exit_code: number | null;
}

export interface JobStarted {
  readonly type: "job_started";
  readonly job_id: string;
  readonly command: string;
}

export interface JobEnded {
  readonly type: "job_ended";
  readonly job_id: string;
  readonly command: string;
  readonly exit_code: number | null;
}

/** The stream opened again after a gap, in which anything may have changed. */
export interface Resync {
  readonly type: "resync";
}

export type Notice = FileChanged | AttemptChanged | ProgressChanged | RunStarted | RunEnded | JobStarted | JobEnded | Resync;

export const NOTICE_TYPES = ["file_changed", "attempt_changed", "progress_changed", "run_started", "run_ended", "job_started", "job_ended"] as const;

/** `open` while it streams; `reconnecting` while the browser tries again; `paused` while the tab
 * is hidden; `lost` once the server refused it, as after a restart. */
export type StreamState = "connecting" | "open" | "reconnecting" | "paused" | "lost";

export type NoticeListener = (notice: Notice) => void;

/** What the stream uses of an `EventSource`. */
export interface EventSourceLike extends EventTarget {
  readonly readyState: number;
  close(): void;
}

export type OpenSource = (url: string) => EventSourceLike;

/** What the stream uses of `document`: whether the tab shows, and `visibilitychange`. */
export interface Visibility extends EventTarget {
  readonly hidden: boolean;
}

/** `EventSource.CLOSED`: the source gave up, as on a refusal, and does not try again. */
const CLOSED = 2;
const VISIBILITY_CHANGE = "visibilitychange";

export class NotificationStream {
  readonly #open: OpenSource;
  readonly #visibility: Visibility;
  readonly #onState: (state: StreamState) => void;
  readonly #listeners = new Set<NoticeListener>();
  #source: EventSourceLike | null = null;
  #opened = false;
  #closed = false;

  constructor(open: OpenSource, visibility: Visibility, onState: (state: StreamState) => void = () => {}) {
    this.#open = open;
    this.#visibility = visibility;
    this.#onState = onState;
    visibility.addEventListener(VISIBILITY_CHANGE, this.#onVisibility);
    if (visibility.hidden) onState("paused");
    else this.#connect();
  }

  /** Calls `listener` with every notice; the function returned removes it. */
  subscribe(listener: NoticeListener): () => void {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }

  close(): void {
    this.#closed = true;
    this.#disconnect();
    this.#visibility.removeEventListener(VISIBILITY_CHANGE, this.#onVisibility);
  }

  #connect(): void {
    this.#onState("connecting");
    const source = this.#open(EVENTS_URL);
    source.addEventListener("open", () => {
      if (this.#opened) this.#emit({ type: "resync" });
      this.#opened = true;
      this.#onState("open");
    });
    source.addEventListener("error", () => {
      if (source.readyState !== CLOSED) {
        this.#onState("reconnecting");
        return;
      }
      if (this.#source === source) this.#source = null;
      this.#onState("lost");
    });
    for (const type of NOTICE_TYPES) {
      source.addEventListener(type, (event) => this.#emit({ type, ...JSON.parse((event as MessageEvent<string>).data) } as Notice));
    }
    this.#source = source;
  }

  #disconnect(): void {
    this.#source?.close();
    this.#source = null;
  }

  #emit(notice: Notice): void {
    for (const listener of this.#listeners) listener(notice);
  }

  /** Hidden, the tab holds no stream; shown again, it opens one, even after a refusal. */
  readonly #onVisibility = (): void => {
    if (this.#closed) return;
    if (this.#visibility.hidden) {
      this.#disconnect();
      this.#onState("paused");
    } else if (this.#source === null) {
      this.#connect();
    }
  };
}
