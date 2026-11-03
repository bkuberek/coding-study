import assert from "node:assert/strict";
import { test } from "node:test";

import {
  completionOptions,
  completionRequest,
  completionResult,
  type CompletionItem,
  insertedText,
  completionMode,
  kindType,
  ResolveOnce,
  VALID_FOR_COMPLETE,
} from "../src/code-intelligence/completion.ts";

function item(fields: Partial<CompletionItem>): CompletionItem {
  return { label: "heappush", ...fields };
}

test("an item inserts its label when it says nothing else", () => {
  assert.equal(insertedText(item({})), "heappush");
});

test("an item inserts its insertText in place of its label", () => {
  assert.equal(insertedText(item({ insertText: "heappush(" })), "heappush(");
});

test("an item inserts the newText of its textEdit before its insertText", () => {
  assert.equal(insertedText(item({ insertText: "a", textEdit: { newText: "b", range: { start: { line: 0, character: 0 }, end: { line: 0, character: 1 } } } })), "b");
});

test("an item that is a snippet inserts its label, never placeholders", () => {
  assert.equal(insertedText(item({ insertText: "heappush(${1:heap})", insertTextFormat: 2 })), "heappush");
});

test("an InsertReplaceEdit inserts its newText", () => {
  const edit = { newText: "c", insert: { start: { line: 0, character: 0 }, end: { line: 0, character: 1 } }, replace: { start: { line: 0, character: 0 }, end: { line: 0, character: 2 } } };
  assert.equal(insertedText(item({ textEdit: edit })), "c");
});

test("the kinds map to CodeMirror's icons", () => {
  assert.deepEqual([2, 3, 6, 7, 9, 14, 21].map(kindType), ["method", "function", "variable", "class", "namespace", "keyword", "constant"]);
});

test("a kind the page does not know has no icon", () => {
  assert.equal(kindType(99), undefined);
  assert.equal(kindType(undefined), undefined);
});

test("options keep every label, in the order the server sent", () => {
  const options = completionOptions([item({ label: "b" }), item({ label: "a" })]);
  assert.deepEqual(options.map((option) => option.label), ["b", "a"]);
});

test("the item that sorts first has the highest boost", () => {
  const [later, earlier] = completionOptions([item({ label: "a", sortText: "2" }), item({ label: "b", sortText: "1" })]);
  assert.ok((earlier?.boost ?? 0) > (later?.boost ?? 0));
});

test("an option has the item's kind as its type", () => {
  assert.equal(completionOptions([item({ kind: 3 })])[0]?.type, "function");
});

test("a detail of the list shows beside the label as text", () => {
  assert.equal(completionOptions([item({ labelDetails: { detail: "(heap, item)" } })])[0]?.detail, "(heap, item)");
});

test("a label that is markup stays text", () => {
  assert.equal(completionOptions([item({ label: "<b>x</b>" })])[0]?.label, "<b>x</b>");
});

test("a typed word asks for completion as invoked", () => {
  assert.deepEqual(completionRequest({ explicit: false, word: "so", before: "o", triggers: ["."] }), { triggerKind: 1 });
});

test("a trigger character asks as a trigger", () => {
  assert.deepEqual(completionRequest({ explicit: false, word: "", before: ".", triggers: ["."] }), { triggerKind: 2, triggerCharacter: "." });
});

test("Ctrl-Space with nothing typed asks as invoked", () => {
  assert.deepEqual(completionRequest({ explicit: true, word: "", before: " ", triggers: ["."] }), { triggerKind: 1 });
});

test("nothing typed and not asked for is no request", () => {
  assert.equal(completionRequest({ explicit: false, word: "", before: " ", triggers: ["."] }), null);
});

test("a trigger character wins over a word before it", () => {
  assert.deepEqual(completionRequest({ explicit: false, word: "x", before: ".", triggers: ["."] }), { triggerKind: 2, triggerCharacter: "." });
});

test("a complete list stays valid while a word is typed", () => {
  assert.equal(VALID_FOR_COMPLETE.test("heapp"), true);
  assert.equal(VALID_FOR_COMPLETE.test("heap."), false);
});

test("an incomplete list is asked for again at every character", () => {
  const source = completionResult({ items: [item({})], isIncomplete: true }, 5);
  assert.equal(source?.validFor, undefined);
});

test("a complete list is valid for words", () => {
  assert.equal(completionResult({ items: [item({})], isIncomplete: false }, 5)?.validFor, VALID_FOR_COMPLETE);
});

test("a list starts where the word starts", () => {
  assert.equal(completionResult({ items: [item({})] }, 7)?.from, 7);
});

test("a bare array of items is a complete list", () => {
  assert.equal(completionResult([item({})] as never, 0)?.options.length, 1);
});

test("a null answer is no list", () => {
  assert.equal(completionResult(null, 0), null);
});

test("an answer with no items is no list", () => {
  assert.equal(completionResult({ items: [] }, 0), null);
});

test("an item is resolved once however often its panel opens", async () => {
  let calls = 0;
  const once = new ResolveOnce<CompletionItem>(async (found) => {
    calls += 1;
    return { ...found, detail: "def heappush()" };
  });
  const entry = item({});
  const [a, b] = await Promise.all([once.resolve(entry), once.resolve(entry)]);
  assert.deepEqual([calls, a?.detail, b?.detail], [1, "def heappush()", "def heappush()"]);
});

test("two items are resolved separately", async () => {
  let calls = 0;
  const once = new ResolveOnce<CompletionItem>(async (found) => {
    calls += 1;
    return found;
  });
  await once.resolve(item({ label: "a" }));
  await once.resolve(item({ label: "b" }));
  assert.equal(calls, 2);
});

test("an item whose resolve fails shows no panel, and is not asked again", async () => {
  let calls = 0;
  const once = new ResolveOnce<CompletionItem>(async () => {
    calls += 1;
    throw new Error("boom");
  });
  const entry = item({});
  assert.deepEqual([await once.resolve(entry), await once.resolve(entry), calls], [null, null, 1]);
});

test("the server completes where autocomplete applies and its session is ready", () => {
  assert.equal(completionMode(true, true), "server");
});

test("the editor's own completion stands in while the session is not ready", () => {
  assert.equal(completionMode(true, false), "editor");
});

test("there is no completion at all while autocomplete does not apply", () => {
  assert.deepEqual([completionMode(false, true), completionMode(false, false)], ["none", "none"]);
});
