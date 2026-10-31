import assert from "node:assert/strict";
import { test } from "node:test";

import { baseName, creates, fileActions, fileScope, joinPath, nameIssue, parentOf } from "../src/page/fileRules.ts";

const STARTER = { origin: "starter", state: "unchanged", size: 10 };

test("a project's files are a folder of their own", () => {
  assert.equal(fileScope({ kind: "project", language: "python" }), "project");
});

test("a Java, Kotlin or Go single-file problem has a package", () => {
  const scopes = ["java", "kotlin", "go"].map((language) => fileScope({ kind: "function", language }));
  assert.deepEqual(scopes, ["package", "package", "package"]);
});

test("a Python, TypeScript or Rust problem and an item have one file", () => {
  const attempts = [
    { kind: "function", language: "python" },
    { kind: "design", language: "typescript" },
    { kind: "concurrent", language: "rust" },
    { kind: "item", language: null },
  ];
  assert.deepEqual(attempts.map(fileScope), ["single", "single", "single", "single"]);
});

test("a project creates files and folders", () => {
  assert.deepEqual(creates("project"), { files: true, folders: true });
});

test("a package creates files only, directly in it", () => {
  assert.deepEqual(creates("package"), { files: true, folders: false });
});

test("one file creates nothing", () => {
  assert.deepEqual(creates("single"), { files: false, folders: false });
});

test("a project file can be renamed and deleted", () => {
  const actions = fileActions("project", STARTER);
  assert.deepEqual([actions.rename, actions.delete], [true, true]);
});

test("an unchanged starter file has nothing to restore", () => {
  assert.equal(fileActions("project", STARTER).restore, false);
});

test("a modified or deleted starter or test file can be restored", () => {
  const entries = [
    { origin: "starter", state: "modified", size: 10 },
    { origin: "starter", state: "deleted", size: null },
    { origin: "level", state: "modified", size: 10 },
  ];
  assert.deepEqual(
    entries.map((entry) => fileActions("project", entry).restore),
    [true, true, true],
  );
});

test("a file you added has nothing to restore", () => {
  assert.equal(fileActions("project", { origin: "yours", state: "added", size: 3 }).restore, false);
});

test("a deleted file can only be restored", () => {
  const actions = fileActions("project", { origin: "starter", state: "deleted", size: null });
  assert.deepEqual([actions.rename, actions.delete], [false, false]);
});

test("a package's files can be renamed and deleted, never restored", () => {
  const actions = fileActions("package", { origin: "yours", state: null, size: 3 });
  assert.deepEqual([actions.rename, actions.delete, actions.restore], [true, true, false]);
});

test("one file can be neither renamed, deleted nor restored", () => {
  const actions = fileActions("single", { origin: "stub", state: null, size: 3 });
  assert.deepEqual([actions.rename, actions.delete, actions.restore], [false, false, false]);
});

test("a name may hold folders in a project", () => {
  assert.equal(nameIssue("project", null, "models/account.py"), null);
});

test("a name must say something", () => {
  assert.equal(nameIssue("project", null, "  "), "type a name");
});

test("a name stays inside the folder", () => {
  const issues = ["../x.py", "a/./b.py", "a//b.py", "/etc/hosts", "a\\b.py"].map((name) => nameIssue("project", null, name));
  assert.deepEqual(issues, [
    "no . or .. or empty folder in a name",
    "no . or .. or empty folder in a name",
    "no . or .. or empty folder in a name",
    "a name is relative to its folder",
    "use / between folders, not \\",
  ]);
});

test("a package's file goes directly in it with the language's extension", () => {
  assert.deepEqual(
    [nameIssue("package", ".java", "Helper.java"), nameIssue("package", ".java", "util/Helper.java"), nameIssue("package", ".java", "Helper.kt")],
    [null, "a file of this package goes directly in it", "end the name with .java"],
  );
});

test("paths join and split at their last folder", () => {
  assert.deepEqual(
    [joinPath("", "a.py"), joinPath("bank", "a.py"), parentOf("bank/models/a.py"), parentOf("a.py"), baseName("bank/a.py")],
    ["a.py", "bank/a.py", "bank/models", "", "a.py"],
  );
});
