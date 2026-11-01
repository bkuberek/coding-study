import assert from "node:assert/strict";
import { test } from "node:test";

import { EVENTS_URL, type EventSourceLike, type Notice, NotificationStream, type StreamState, type Visibility } from "../src/page/notifications.ts";

const CONNECTING = 0;
const CLOSED = 2;

class FakeSource extends EventTarget implements EventSourceLike {
  readonly url: string;
  readyState = CONNECTING;
  closed = false;

  constructor(url: string) {
    super();
    this.url = url;
  }

  close(): void {
    this.closed = true;
    this.readyState = CLOSED;
  }

  opens(): void {
    this.readyState = 1;
    this.dispatchEvent(new Event("open"));
  }

  sends(type: string, data: object): void {
    this.dispatchEvent(new MessageEvent(type, { data: JSON.stringify(data) }));
  }

  fails(readyState: number): void {
    this.readyState = readyState;
    this.dispatchEvent(new Event("error"));
  }
}

class FakeTab extends EventTarget implements Visibility {
  hidden = false;

  turns(hidden: boolean): void {
    this.hidden = hidden;
    this.dispatchEvent(new Event("visibilitychange"));
  }
}

/** A stream over fake sources: every source it opened, every state, and every notice. */
function streaming(tab = new FakeTab()) {
  const sources: FakeSource[] = [];
  const states: StreamState[] = [];
  const notices: Notice[] = [];
  const stream = new NotificationStream(
    (url) => {
      const source = new FakeSource(url);
      sources.push(source);
      return source;
    },
    tab,
    (state) => states.push(state),
  );
  stream.subscribe((notice) => notices.push(notice));
  const last = () => sources[sources.length - 1] as FakeSource;
  return { stream, tab, sources, states, notices, last };
}

test("a shown tab opens the notification stream", () => {
  const { sources } = streaming();
  assert.deepEqual(sources.map((source) => source.url), [EVENTS_URL]);
});

test("a notice reaches every listener with its type and fields", () => {
  const { last, notices } = streaming();
  last().opens();
  last().sends("file_changed", { attempt_id: 3, path: "bank/bank.py", sha256: "ab" });
  assert.deepEqual(notices, [{ type: "file_changed", attempt_id: 3, path: "bank/bank.py", sha256: "ab" }]);
});

test("the first opening is no resync", () => {
  const { last, notices } = streaming();
  last().opens();
  assert.deepEqual(notices, []);
});

test("a hidden tab closes its stream", () => {
  const { last, tab } = streaming();
  last().opens();
  tab.turns(true);
  assert.equal(last().closed, true);
});

test("a hidden tab's stream is paused", () => {
  const { last, tab, states } = streaming();
  last().opens();
  tab.turns(true);
  assert.equal(states.at(-1), "paused");
});

test("a tab that loads hidden opens no stream until it shows", () => {
  const tab = new FakeTab();
  tab.hidden = true;
  const { sources } = streaming(tab);
  assert.equal(sources.length, 0);
});

test("a tab shown again opens a new stream and tells the views to read again", () => {
  const { last, tab, sources, notices } = streaming();
  last().opens();
  tab.turns(true);
  tab.turns(false);
  last().opens();
  assert.deepEqual([sources.length, notices], [2, [{ type: "resync" }]]);
});

test("a stream the browser reconnects tells the views to read again", () => {
  const { last, notices } = streaming();
  last().opens();
  last().fails(CONNECTING);
  last().opens();
  assert.deepEqual(notices, [{ type: "resync" }]);
});

test("a stream the browser tries again is reconnecting", () => {
  const { last, states } = streaming();
  last().opens();
  last().fails(CONNECTING);
  assert.equal(states.at(-1), "reconnecting");
});

test("a stream the server refused is lost", () => {
  const { last, states } = streaming();
  last().fails(CLOSED);
  assert.equal(states.at(-1), "lost");
});

test("a tab shown again after a refusal tries a new stream", () => {
  const { last, tab, sources } = streaming();
  last().fails(CLOSED);
  tab.turns(true);
  tab.turns(false);
  assert.equal(sources.length, 2);
});

test("a closed stream ignores the tab showing again", () => {
  const { stream, tab, sources } = streaming();
  stream.close();
  tab.turns(true);
  tab.turns(false);
  assert.equal(sources.length, 1);
});
