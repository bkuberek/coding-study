import assert from "node:assert/strict";
import { afterEach, beforeEach, mock, test } from "node:test";

import { type AttachRequest, CodeIntelligence, HIDDEN_CLOSE_MS } from "../src/code-intelligence/manager.ts";
import { FILE_SAVED_EVENT } from "../src/page/api.ts";
import { FakeSocket } from "./fake-socket.ts";

const MINUTE_MS = 60_000;

let sockets: FakeSocket[];
let preferenceListeners: Set<() => void>;
let enabled: boolean;
let page: EventTarget & { hidden: boolean };
let manager: CodeIntelligence;

function newManager(): CodeIntelligence {
  return new CodeIntelligence(
    {
      enabled: () => enabled,
      onPreferences: (listener) => {
        preferenceListeners.add(listener);
        return () => preferenceListeners.delete(listener);
      },
    },
    {
      origin: { protocol: "http:", host: "localhost" },
      createSocket: (url) => {
        const socket = new FakeSocket(url);
        sockets.push(socket);
        return socket as unknown as WebSocket;
      },
    },
  );
}

function request(overrides: Partial<AttachRequest> = {}): AttachRequest {
  const editor = { setIntelligence() {}, setLiveDiagnostics() {} } as unknown as AttachRequest["editor"];
  return {
    editor,
    csrf: "token",
    attemptId: 7,
    path: "a.py",
    languageId: "python",
    workspace: "/ws",
    root: "python/practice",
    idleS: 60,
    ...overrides,
  };
}

async function flush(): Promise<void> {
  for (let turn = 0; turn < 5; turn++) await Promise.resolve();
}

async function ready(socket: FakeSocket): Promise<void> {
  socket.accept();
  const initialize = socket.messages().find((message) => message.method === "initialize");
  socket.receive({ jsonrpc: "2.0", id: initialize?.id, result: { capabilities: {} } });
  await flush();
}

function hide(hidden: boolean): void {
  page.hidden = hidden;
  page.dispatchEvent(new Event("visibilitychange"));
}

function saved(attemptId: number, path: string): void {
  (globalThis as unknown as { window: EventTarget }).window.dispatchEvent(
    new CustomEvent(FILE_SAVED_EVENT, { detail: { attemptId, path, sha256: "x" } }),
  );
}

beforeEach(() => {
  mock.timers.enable({ apis: ["setTimeout"] });
  sockets = [];
  preferenceListeners = new Set();
  enabled = true;
  page = Object.assign(new EventTarget(), { hidden: false });
  Object.assign(globalThis, { document: page, window: new EventTarget() });
  manager = newManager();
});

afterEach(() => {
  manager.dispose();
  mock.timers.reset();
});

test("two files of one root share a session", () => {
  manager.attach(request());
  manager.attach(request({ path: "b.py" }));
  assert.equal(sockets.length, 1);
});

test("another root has a session of its own", () => {
  manager.attach(request());
  manager.attach(request({ root: "python/other" }));
  assert.equal(sockets.length, 2);
});

test("a later attempt in the same root reuses the session and the next socket asks for it", () => {
  manager.attach(request());
  manager.attach(request({ attemptId: 9, path: "b.py" }));
  sockets[0]?.drop(1006);
  mock.timers.tick(1000);
  assert.deepEqual([sockets.length, sockets[1]?.url.endsWith("attempt_id=9")], [2, true]);
});

test("a tab hidden for five minutes closes its sessions", () => {
  manager.attach(request());
  hide(true);
  mock.timers.tick(HIDDEN_CLOSE_MS - 1);
  assert.equal(sockets[0]?.closeCode(), null);
  mock.timers.tick(1);
  assert.equal(sockets[0]?.closeCode(), 1000);
});

test("a tab shown again opens its suspended sessions", () => {
  manager.attach(request());
  hide(true);
  mock.timers.tick(HIDDEN_CLOSE_MS);
  hide(false);
  assert.equal(sockets.length, 2);
});

test("a tab shown before the five minutes keeps its sessions", () => {
  manager.attach(request());
  hide(true);
  mock.timers.tick(MINUTE_MS);
  hide(false);
  mock.timers.tick(HIDDEN_CLOSE_MS);
  assert.deepEqual([sockets.length, sockets[0]?.closeCode()], [1, null]);
});

test("turning the preference off closes every session at once", () => {
  manager.attach(request());
  manager.attach(request({ root: "python/other" }));
  enabled = false;
  for (const listener of preferenceListeners) listener();
  assert.deepEqual(sockets.map((socket) => socket.closeCode()), [1000, 1000]);
});

test("a preference change that leaves it on closes nothing", () => {
  manager.attach(request());
  for (const listener of preferenceListeners) listener();
  assert.equal(sockets[0]?.closeCode(), null);
});

test("a save of an attached file tells the server, by the file's URI", async () => {
  manager.attach(request());
  await ready(sockets[0]!);
  saved(7, "a.py");
  await flush();
  const didSave = sockets[0]?.messages().find((message) => message.method === "textDocument/didSave");
  assert.deepEqual((didSave as { params?: unknown } | undefined)?.params, { textDocument: { uri: "file:///ws/python/practice/a.py" } });
});

test("a save of another file, or of another attempt's, tells nobody", async () => {
  manager.attach(request());
  await ready(sockets[0]!);
  saved(7, "b.py");
  saved(8, "a.py");
  await flush();
  assert.equal(sockets[0]?.messages().some((message) => message.method === "textDocument/didSave"), false);
});

test("a detached file hears no save", async () => {
  const attachment = manager.attach(request());
  await ready(sockets[0]!);
  attachment.detach();
  saved(7, "a.py");
  await flush();
  assert.equal(sockets[0]?.messages().some((message) => message.method === "textDocument/didSave"), false);
});

test("an attachment says its session's state", async () => {
  const attachment = manager.attach(request());
  assert.equal(attachment.state.kind, "starting");
  await ready(sockets[0]!);
  assert.equal(attachment.state.kind, "ready");
});

test("Restart on an attachment opens its session again", () => {
  const attachment = manager.attach(request());
  sockets[0]?.drop(4002, "exit 1: boom");
  attachment.restart();
  assert.equal(sockets.length, 2);
});
