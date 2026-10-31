import assert from "node:assert/strict";
import { test } from "node:test";

import { languageForPath } from "../src/languages.ts";

const BY_EXTENSION = {
  "solution.py": "python",
  "stubs.pyi": "python",
  "bank.ts": "typescript",
  "bank.mts": "typescript",
  "bank.cts": "typescript",
  "view.tsx": "tsx",
  "bank.js": "javascript",
  "bank.mjs": "javascript",
  "bank.cjs": "javascript",
  "view.jsx": "jsx",
  "Bank.java": "java",
  "Bank.kt": "kotlin",
  "build.gradle.kts": "kotlin",
  "bank.go": "go",
  "lib.rs": "rust",
  "tests.json": "json",
  "Cargo.toml": "toml",
  "meta.yaml": "yaml",
  "config.yml": "yaml",
  "README.md": "markdown",
  "notes.markdown": "markdown",
} as const;

for (const [path, language] of Object.entries(BY_EXTENSION)) {
  test(`${path} is ${language}`, () => {
    assert.equal(languageForPath(path), language);
  });
}

test("the extension decides, not the directories", () => {
  assert.equal(languageForPath("src/bank.d/accounts.py"), "python");
});

test("only the last extension counts", () => {
  assert.equal(languageForPath("bank.test.ts"), "typescript");
});

test("an extension in capitals counts", () => {
  assert.equal(languageForPath("NOTES.MD"), "markdown");
});

test("a hidden file with an extension has its language", () => {
  assert.equal(languageForPath(".eslintrc.json"), "json");
});

test("a hidden file without an extension has none", () => {
  assert.equal(languageForPath(".gitignore"), null);
});

test("a file without an extension has none", () => {
  assert.equal(languageForPath("Makefile"), null);
});

test("a dot in a directory name is not an extension", () => {
  assert.equal(languageForPath("bank.d/Makefile"), null);
});

test("a name ending in a dot has none", () => {
  assert.equal(languageForPath("bank."), null);
});

test("an unknown extension has none", () => {
  assert.equal(languageForPath("archive.tar.gz"), null);
});

test("an extension named like an object property has none", () => {
  assert.equal(languageForPath("bank.constructor"), null);
});
