import assert from "node:assert/strict";
import { test } from "node:test";

import { fileUri, languageIdFor, rootUri, serverLanguageFor } from "../src/code-intelligence/documents.ts";

test("a file's URI is the workspace, the root and the path", () => {
  assert.equal(fileUri("/home/me/ws", "python", "two_sum.py"), "file:///home/me/ws/python/two_sum.py");
});

test("each segment is percent-encoded as encodeURIComponent does", () => {
  assert.equal(fileUri("/home/me/my ws", "projects/bank", "a b/c#d.py"), "file:///home/me/my%20ws/projects/bank/a%20b/c%23d.py");
});

test("the root's URI has no trailing slash", () => {
  assert.equal(rootUri("/home/me/ws", "python"), "file:///home/me/ws/python");
});

test("a Windows workspace keeps its drive letter", () => {
  assert.equal(fileUri("C:\\Users\\me\\ws", "python", "x.py"), "file:///C:/Users/me/ws/python/x.py");
});

test("Python files are python", () => {
  assert.deepEqual([languageIdFor("a.py"), languageIdFor("a.pyi")], ["python", "python"]);
});

test("TypeScript's files have the ids tsserver knows", () => {
  assert.deepEqual(
    ["a.ts", "a.mts", "a.cts", "a.tsx", "a.js", "a.mjs", "a.jsx"].map(languageIdFor),
    ["typescript", "typescript", "typescript", "typescriptreact", "javascript", "javascript", "javascriptreact"],
  );
});

test("Java files are java, the id JDT LS knows", () => {
  assert.equal(languageIdFor("Solution.java"), "java");
});

test("Go files are go, the id gopls knows", () => {
  assert.equal(languageIdFor("practice/two_sum/two_sum.go"), "go");
});

test("Rust files are rust, the id rust-analyzer knows", () => {
  assert.equal(languageIdFor("practice/two_sum.rs"), "rust");
});

test("a Kotlin file has no id while Kotlin has no server", () => {
  assert.equal(languageIdFor("Solution.kt"), null);
});

test("a file with no language server id has none", () => {
  assert.equal(languageIdFor("notes.md"), null);
});

test("the editor's languages map to the catalog's", () => {
  assert.deepEqual(
    ["a.py", "a.ts", "a.tsx", "a.js", "a.java", "a.kt", "a.go", "a.rs", "a.md", "a.toml"].map(serverLanguageFor),
    ["python", "typescript", "typescript", "typescript", "java", "kotlin", "go", "rust", null, null],
  );
});
