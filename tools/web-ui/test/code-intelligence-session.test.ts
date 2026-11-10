import assert from "node:assert/strict";
import { afterEach, beforeEach, mock, test } from "node:test";

import { Session, type SessionOptions } from "../src/code-intelligence/session.ts";
import { sessionUrl } from "../src/code-intelligence/transport.ts";
import type { SessionState } from "../src/page/intelligence-state.ts";
import { FakeSocket } from "./fake-socket.ts";

let sockets: FakeSocket[];
let states: SessionState[];
let idle: number;

function newSession(overrides: Partial<SessionOptions> = {}): Session {
  const session = new Session({
    attemptId: 7,
    origin: { protocol: "http:", host: "localhost" },
    csrf: "token",
    rootUri: "file:///ws/python",
    idleMs: 60_000,
    createSocket: (url) => {
      const socket = new FakeSocket(url);
      sockets.push(socket);
      return socket as unknown as WebSocket;
    },
    onIdle: () => {
      idle += 1;
    },
    ...overrides,
  });
  session.onState((state) => states.push(state));
  return session;
}

/** Lets the promise callbacks of the client run. */
async function flush(): Promise<void> {
  for (let turn = 0; turn < 5; turn++) await Promise.resolve();
}

async function becomeReady(socket: FakeSocket): Promise<void> {
  socket.accept();
  const initialize = socket.messages().find((message) => message.method === "initialize");
  socket.receive({ jsonrpc: "2.0", id: initialize?.id, result: { capabilities: {} } });
  await flush();
}

const last = () => sockets[sockets.length - 1]!;
const kinds = () => states.map((state) => state.kind);

beforeEach(() => {
  mock.timers.enable({ apis: ["setTimeout"] });
  sockets = [];
  states = [];
  idle = 0;
});

afterEach(() => {
  mock.timers.reset();
});

test("the session URL is the page's own host and the attempt", () => {
  assert.equal(sessionUrl({ protocol: "http:", host: "127.0.0.1:8123" }, 7), "ws://127.0.0.1:8123/api/v1/code-intelligence?attempt_id=7");
});

test("a page served over https opens a wss URL", () => {
  assert.equal(sessionUrl({ protocol: "https:", host: "localhost:1" }, 3), "wss://localhost:1/api/v1/code-intelligence?attempt_id=3");
});

test("a new session is starting and opens its socket", () => {
  const session = newSession();
  session.start();
  assert.deepEqual([session.state.kind, sockets.length, sockets[0]?.url], ["starting", 1, "ws://localhost/api/v1/code-intelligence?attempt_id=7"]);
});

test("the CSRF token is the first message and initialize follows", () => {
  newSession().start();
  last().accept();
  const [first, second] = last().messages();
  assert.deepEqual([first, second?.method], [{ csrf: "token" }, "initialize"]);
});

test("the session is ready once initialize is answered, and initialized goes out", async () => {
  const session = newSession();
  session.start();
  await becomeReady(last());
  assert.deepEqual([session.state.kind, last().messages().some((m) => m.method === "initialized")], ["ready", true]);
});

test("a dropped connection shows reconnecting and tries again after 1 second", async () => {
  const session = newSession();
  session.start();
  await becomeReady(last());
  last().drop(1006);
  assert.equal(session.state.kind, "reconnecting");
  mock.timers.tick(999);
  assert.equal(sockets.length, 1);
  mock.timers.tick(1);
  assert.equal(sockets.length, 2);
});

test("the tries wait 1, 2 and 5 seconds, and the fourth failure stops the session", () => {
  const session = newSession();
  session.start();
  for (const wait of [1000, 2000, 5000]) {
    last().drop(1006);
    assert.equal(session.state.kind, "reconnecting");
    mock.timers.tick(wait);
  }
  last().drop(1006);
  assert.deepEqual(session.state, { kind: "stopped", why: "", reason: "" });
  assert.equal(sockets.length, 4);
});

test("a try that gets through starts the count again", async () => {
  const session = newSession();
  session.start();
  last().drop(1006);
  mock.timers.tick(1000);
  await becomeReady(last());
  last().drop(1006);
  mock.timers.tick(1000);
  assert.equal(sockets.length, 3);
});

test("a server that exited stops the session with its exit code and does not try again", async () => {
  const session = newSession();
  session.start();
  await becomeReady(last());
  last().drop(4002, "exit 1: boom");
  mock.timers.tick(60_000);
  assert.deepEqual([session.state, sockets.length], [{ kind: "stopped", why: "exit 1", reason: "exit 1: boom" }, 1]);
});

test("a fifth session stops with the limit", () => {
  const session = newSession();
  session.start();
  last().drop(4003, "at most 4 code intelligence sessions run at once; close one in another tab");
  assert.equal((session.state as { why: string }).why, "4 sessions running");
});

test("a session whose server needs Docker waits calmly and does not try again", () => {
  const session = newSession();
  session.start();
  last().drop(4004, "Docker is not running");
  mock.timers.tick(60_000);
  assert.deepEqual([session.state, sockets.length], [{ kind: "needs-docker", why: "Docker is not running", reason: "Docker is not running" }, 1]);
});

test("Restart opens the session again, from starting", async () => {
  const session = newSession();
  session.start();
  last().drop(4002, "exit 1: boom");
  session.restart();
  assert.deepEqual([session.state.kind, sockets.length], ["starting", 2]);
  await becomeReady(last());
  assert.equal(session.state.kind, "ready");
});

test("Restart during a wait for a try opens one socket, not two", () => {
  const session = newSession();
  session.start();
  last().drop(1006);
  session.restart();
  mock.timers.tick(10_000);
  assert.equal(sockets.length, 2);
});

test("a stale socket's close changes nothing", () => {
  const session = newSession();
  session.start();
  const first = last();
  session.restart();
  first.drop(4002, "exit 1: boom");
  assert.equal(session.state.kind, "starting");
});

test("closing the session closes the socket with 1000 and does not try again", async () => {
  const session = newSession();
  session.start();
  await becomeReady(last());
  const socket = last();
  session.close();
  socket.drop(1000);
  mock.timers.tick(60_000);
  assert.deepEqual([socket.closeCode(), sockets.length], [1000, 1]);
});

test("a session with no files is closed after its idle time", async () => {
  const session = newSession();
  session.start();
  await becomeReady(last());
  const socket = last();
  session.filesChanged(1);
  session.filesChanged(0);
  mock.timers.tick(59_999);
  assert.equal(socket.closeCode(), null);
  mock.timers.tick(1);
  assert.deepEqual([socket.closeCode(), idle], [1000, 1]);
});

test("a file opened before the idle time ends keeps the session", async () => {
  const session = newSession();
  session.start();
  await becomeReady(last());
  session.filesChanged(0);
  mock.timers.tick(30_000);
  session.filesChanged(1);
  mock.timers.tick(60_000);
  assert.deepEqual([last().closeCode(), idle], [null, 0]);
});

test("a suspended session closes its socket and resume opens it again", async () => {
  const session = newSession();
  session.start();
  await becomeReady(last());
  const socket = last();
  session.suspend();
  socket.drop(1000);
  mock.timers.tick(60_000);
  assert.equal(sockets.length, 1);
  session.resume();
  assert.deepEqual([session.state.kind, sockets.length], ["starting", 2]);
});

test("the next attempt of the root is the one a try asks for", () => {
  const session = newSession();
  session.start();
  session.useAttempt(9);
  last().drop(1006);
  mock.timers.tick(1000);
  assert.match(last().url, /attempt_id=9$/);
});

test("the states are announced once each, in order", async () => {
  const session = newSession();
  session.start();
  await becomeReady(last());
  last().drop(1006);
  assert.deepEqual(kinds(), ["ready", "reconnecting"]);
});
