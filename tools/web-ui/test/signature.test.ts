import assert from "node:assert/strict";
import { test } from "node:test";

import { activeSignature, labelParts, type SignatureHelp, typedTrigger } from "../src/code-intelligence/signature.ts";

const PUSH = "heappush(heap: list[T], item: T) -> None";

function help(fields: Partial<SignatureHelp> = {}): SignatureHelp {
  return {
    signatures: [
      { label: PUSH, parameters: [{ label: "heap: list[T]" }, { label: "item: T" }] },
      { label: "heappush(heap)", parameters: [{ label: "heap" }] },
    ],
    ...fields,
  };
}

test("the active signature is the first unless the answer says another", () => {
  assert.equal(activeSignature(help())?.signature.label, PUSH);
  assert.equal(activeSignature(help({ activeSignature: 1 }))?.signature.label, "heappush(heap)");
});

test("an active signature past the list is the first", () => {
  assert.equal(activeSignature(help({ activeSignature: 5 }))?.signature.label, PUSH);
});

test("the active parameter is the answer's, else the first", () => {
  assert.equal(activeSignature(help())?.parameter, 0);
  assert.equal(activeSignature(help({ activeParameter: 1 }))?.parameter, 1);
});

test("a signature's own active parameter wins over the answer's", () => {
  const found = activeSignature({ signatures: [{ label: PUSH, parameters: [{ label: "a" }, { label: "b" }], activeParameter: 1 }], activeParameter: 0 });
  assert.equal(found?.parameter, 1);
});

test("an active parameter past the parameters marks none", () => {
  assert.equal(activeSignature(help({ activeParameter: 2 }))?.parameter, null);
});

test("a null active parameter marks none", () => {
  assert.equal(activeSignature(help({ activeParameter: null }))?.parameter, null);
});

test("an answer without signatures is no signature help", () => {
  assert.equal(activeSignature({ signatures: [] }), null);
});

test("a parameter named by a string is found in the label", () => {
  assert.deepEqual(labelParts({ label: PUSH, parameters: [{ label: "heap: list[T]" }, { label: "item: T" }] }, 1), {
    before: "heappush(heap: list[T], ",
    active: "item: T",
    after: ") -> None",
  });
});

test("a parameter named by offsets is cut from the label", () => {
  assert.deepEqual(labelParts({ label: "f(a, b)", parameters: [{ label: [2, 3] }, { label: [5, 6] }] }, 0), { before: "f(", active: "a", after: ", b)" });
});

test("no active parameter leaves the whole label as it is", () => {
  assert.deepEqual(labelParts({ label: "f(a)", parameters: [{ label: "a" }] }, null), { before: "f(a)", active: "", after: "" });
});

test("a parameter the label does not hold marks nothing", () => {
  assert.deepEqual(labelParts({ label: "f(a)", parameters: [{ label: "zzz" }] }, 0), { before: "f(a)", active: "", after: "" });
});

test("offsets outside the label mark nothing", () => {
  assert.deepEqual(labelParts({ label: "f(a)", parameters: [{ label: [9, 12] }] }, 0), { before: "f(a)", active: "", after: "" });
});

test("a typed trigger character is found in what was inserted", () => {
  assert.equal(typedTrigger("(", ["(", ","]), "(");
});

test("a bracket typed with its closing bracket is a trigger", () => {
  assert.equal(typedTrigger("()", ["(", ","]), "(");
});

test("two characters that are no bracket pair are no trigger", () => {
  assert.equal(typedTrigger("(x", ["(", ","]), null);
});

test("a pasted text is no trigger", () => {
  assert.equal(typedTrigger("f(a, b)", ["(", ","]), null);
});

test("a character that is not a trigger is none", () => {
  assert.equal(typedTrigger("a", ["(", ","]), null);
});

test("nothing inserted is no trigger", () => {
  assert.equal(typedTrigger("", ["("]), null);
});
