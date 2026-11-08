import assert from "node:assert/strict";
import { test } from "node:test";

import {
  classifyTarget,
  definitionTarget,
  isDefinitionClick,
  JumpStack,
  linkTarget,
  type Origin,
  refusalNote,
} from "../src/code-intelligence/navigation.ts";

const ROOT = "file:///ws/python/practice";
const OWN = `${ROOT}/two_sum.py`;
const TREE: ReadonlySet<string> = new Set(["two_sum.py", "test_two_sum.py", "sub dir/helper.py"]);

const START = { line: 4, character: 2 };
const RANGE = { start: START, end: { line: 4, character: 9 } };

test("a Location is its uri and the start of its range", () => {
  assert.deepEqual(definitionTarget({ uri: OWN, range: RANGE }), { uri: OWN, line: 4, character: 2 });
});

test("a list of locations gives the first", () => {
  const second = { uri: `${ROOT}/other.py`, range: { start: { line: 9, character: 0 }, end: { line: 9, character: 1 } } };
  assert.deepEqual(definitionTarget([{ uri: OWN, range: RANGE }, second]), { uri: OWN, line: 4, character: 2 });
});

test("a LocationLink is its targetUri and the start of its targetSelectionRange", () => {
  const link = { targetUri: OWN, targetRange: { start: { line: 1, character: 0 }, end: { line: 8, character: 0 } }, targetSelectionRange: RANGE };
  assert.deepEqual(definitionTarget([link]), { uri: OWN, line: 4, character: 2 });
});

test("a LocationLink without a selection range uses its target range", () => {
  const link = { targetUri: OWN, targetRange: RANGE };
  assert.deepEqual(definitionTarget(link), { uri: OWN, line: 4, character: 2 });
});

test("no location is no target", () => {
  assert.deepEqual([definitionTarget(null), definitionTarget([]), definitionTarget({ nonsense: 1 })], [null, null, null]);
});

test("the file the cursor is in is the same file", () => {
  assert.deepEqual(classifyTarget(OWN, OWN, ROOT, TREE), { kind: "same" });
});

test("another file of the tree is an attempt file", () => {
  assert.deepEqual(classifyTarget(`${ROOT}/test_two_sum.py`, OWN, ROOT, TREE), { kind: "attempt", path: "test_two_sum.py" });
});

test("a path of the tree is decoded from its URI", () => {
  assert.deepEqual(classifyTarget(`${ROOT}/sub%20dir/helper.py`, OWN, ROOT, TREE), { kind: "attempt", path: "sub dir/helper.py" });
});

test("a file inside the root that the tree does not list is a library file", () => {
  assert.deepEqual(classifyTarget(`${ROOT}/.venv/lib/x.py`, OWN, ROOT, TREE), { kind: "library" });
});

test("a file outside the root is a library file", () => {
  assert.deepEqual(classifyTarget("file:///ws/.cs/lsp/builtins.pyi", OWN, ROOT, TREE), { kind: "library" });
});

test("a URI of another scheme is left to the broker to refuse", () => {
  assert.deepEqual(classifyTarget("jdt://contents/java.base/List.class", OWN, ROOT, TREE), { kind: "library" });
});

test("a folder with the root as a prefix is not inside the root", () => {
  assert.deepEqual(classifyTarget("file:///ws/python/practice2/two_sum.py", OWN, ROOT, TREE), { kind: "library" });
});

function refusal(reason: string, path = "python/.venv/big.py") {
  return { code: -32803, message: "refused", data: { reason, path } };
}

test("a file over 4 MiB is named with its line and the reason", () => {
  assert.equal(refusalNote(refusal("too_large"), 119), "python/.venv/big.py:120 · over 4 MiB");
});

test("a file that is not UTF-8 says so", () => {
  assert.equal(refusalNote(refusal("not_text"), 0), "python/.venv/big.py:1 · not UTF-8 text");
});

test("a file that is gone says so", () => {
  assert.equal(refusalNote(refusal("missing"), 0), "python/.venv/big.py:1 · no such file");
});

test("something that is not a regular file says so", () => {
  assert.equal(refusalNote(refusal("not_a_file"), 0), "python/.venv/big.py:1 · not a regular file");
});

test("a URI that is not a file: URI says so", () => {
  assert.equal(refusalNote(refusal("not_a_file_uri", "jdt://x/List.class"), 3), "jdt://x/List.class:4 · not a file: URI");
});

test("the build area is refused without a line", () => {
  assert.equal(refusalNote(refusal("build_area"), 5), "not shown: cstudy's build area");
});

test("a refusal with no reason uses the server's message", () => {
  assert.equal(refusalNote({ code: -32803, message: "refused" }, 5), "refused");
});

test("a refusal that is no object is its text", () => {
  assert.equal(refusalNote(new Error("Request timed out"), 5), "Request timed out");
});

const MAC = { metaKey: true, ctrlKey: false, altKey: false, shiftKey: false };
const CTRL = { metaKey: false, ctrlKey: true, altKey: false, shiftKey: false };

test("Cmd-click goes to the definition on macOS", () => {
  assert.equal(isDefinitionClick(MAC, true), true);
});

test("Ctrl-click does not on macOS, where it is the context menu", () => {
  assert.equal(isDefinitionClick(CTRL, true), false);
});

test("Ctrl-click goes to the definition elsewhere", () => {
  assert.equal(isDefinitionClick(CTRL, false), true);
});

test("Cmd-click does not elsewhere", () => {
  assert.equal(isDefinitionClick(MAC, false), false);
});

test("Alt-Shift with the key held adds a cursor instead", () => {
  assert.equal(isDefinitionClick({ ...CTRL, altKey: true, shiftKey: true }, false), false);
});

test("a plain click is not a definition click", () => {
  assert.equal(isDefinitionClick({ metaKey: false, ctrlKey: false, altKey: false, shiftKey: false }, false), false);
});

function origin(path: string, head = 0): Origin {
  return { tab: { kind: "attempt", path }, head };
}

test("back returns the newest origin first", () => {
  const stack = new JumpStack();
  stack.push(origin("a.py", 1));
  stack.push(origin("b.py", 2));
  assert.deepEqual([stack.pop(() => true), stack.pop(() => true)], [origin("b.py", 2), origin("a.py", 1)]);
});

test("back with nothing recorded gives nothing", () => {
  assert.equal(new JumpStack().pop(() => true), null);
});

test("back skips an origin that can no longer be shown", () => {
  const stack = new JumpStack();
  stack.push(origin("a.py", 1));
  stack.push(origin("b.py", 2));
  assert.deepEqual(stack.pop((found) => found.tab.kind === "attempt" && found.tab.path === "a.py"), origin("a.py", 1));
});

test("the stack keeps the last 50 origins", () => {
  const stack = new JumpStack();
  for (let head = 0; head < 60; head++) stack.push(origin("a.py", head));
  assert.deepEqual([stack.size, stack.pop(() => true)?.head], [50, 59]);
});

test("the oldest origins are the ones dropped", () => {
  const stack = new JumpStack();
  for (let head = 0; head < 51; head++) stack.push(origin("a.py", head));
  let last: Origin | null = null;
  for (let next = stack.pop(() => true); next !== null; next = stack.pop(() => true)) last = next;
  assert.equal(last?.head, 1);
});

const GOROOT_FILE = "file:///go/src/strings/strings.go";

test("a documentation link names its file and gopls's 1-based line and column", () => {
  assert.deepEqual(linkTarget(`${GOROOT_FILE}#314,6`), { uri: GOROOT_FILE, line: 313, character: 5 });
});

test("a link to a line without a column is the start of the line", () => {
  assert.deepEqual(linkTarget(`${GOROOT_FILE}#L12`), { uri: GOROOT_FILE, line: 11, character: 0 });
});

test("a link with an L before the line and a column after it", () => {
  assert.deepEqual(linkTarget(`${GOROOT_FILE}#L12,5`), { uri: GOROOT_FILE, line: 11, character: 4 });
});

test("a link without a fragment is the start of the file", () => {
  assert.deepEqual(linkTarget(GOROOT_FILE), { uri: GOROOT_FILE, line: 0, character: 0 });
});

test("a fragment that names no line is the start of the file", () => {
  assert.deepEqual(linkTarget(`${GOROOT_FILE}#Split`), { uri: GOROOT_FILE, line: 0, character: 0 });
});
