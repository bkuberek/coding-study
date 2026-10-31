import assert from "node:assert/strict";
import { test } from "node:test";

import { fileTree, type TreeNode } from "../src/page/tree.ts";

function names(nodes: readonly TreeNode<{ path: string }>[]): unknown[] {
  return nodes.map((node) => (node.kind === "folder" ? { [node.name]: names(node.children) } : node.name));
}

test("files at the root stay at the root", () => {
  assert.deepEqual(names(fileTree([{ path: "two_sum.py" }])), ["two_sum.py"]);
});

test("files nest under their folders", () => {
  const tree = fileTree([{ path: "bank/bank.py" }, { path: "bank/ledger/entries.py" }, { path: "README.md" }]);
  assert.deepEqual(names(tree), [{ bank: [{ ledger: ["entries.py"] }, "bank.py"] }, "README.md"]);
});

test("folders come before files, each by name", () => {
  const tree = fileTree([{ path: "z.py" }, { path: "tests/a.py" }, { path: "a.py" }, { path: "lib/b.py" }]);
  assert.deepEqual(names(tree), [{ lib: ["b.py"] }, { tests: ["a.py"] }, "a.py", "z.py"]);
});

test("a folder's path is relative to the root", () => {
  const [folder] = fileTree([{ path: "bank/ledger/entries.py" }]);
  assert.ok(folder?.kind === "folder");
  const [inner] = folder.children;
  assert.equal(inner?.path, "bank/ledger");
});

test("a file keeps its whole entry", () => {
  const entry = { path: "bank/bank.py", state: "modified" };
  const [folder] = fileTree([entry]);
  assert.ok(folder?.kind === "folder");
  const [file] = folder.children;
  assert.ok(file?.kind === "file");
  assert.equal(file.file, entry);
});

test("no files make no tree", () => {
  assert.deepEqual(fileTree([]), []);
});
