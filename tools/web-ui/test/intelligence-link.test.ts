import assert from "node:assert/strict";
import { test } from "node:test";

import { type AttemptLanguage, decide } from "../src/page/intelligence.ts";
import type { LanguageState } from "../src/page/types.ts";

const STATES: readonly LanguageState[] = [
  { language: "python", server: "basedpyright", version: "1.40.2", state: "installed", detail: "basedpyright 1.40.2", idle_s: 60 },
  { language: "typescript", server: "typescript-language-server", version: "6.0.3", state: "not_installed", detail: "not installed: run cstudy doctor --fix", idle_s: 60 },
  { language: "go", server: null, version: null, state: "not_available", detail: "not available yet", idle_s: null },
];

const JAVA_ON_JDK_21: readonly LanguageState[] = [
  { language: "java", server: "jdtls", version: "1.63.0", state: "needs_jdk", detail: "needs JDK 25 or 26", idle_s: 300 },
];

const JAVA_INSTALLED: readonly LanguageState[] = [
  { language: "java", server: "jdtls", version: "1.63.0", state: "installed", detail: "jdtls 1.63.0", idle_s: 300 },
];

const INSTALLED_TYPESCRIPT: readonly LanguageState[] = [
  { language: "typescript", server: "typescript-language-server", version: "6.0.3", state: "installed", detail: "typescript-language-server 6.0.3", idle_s: 60 },
];

function attempt(language: string | null): AttemptLanguage {
  return { language, noCodeIntelligence: null };
}

const SERVICE_PROJECT: AttemptLanguage = { language: "typescript", noCodeIntelligence: "service_project" };

test("a Python file of a Python attempt with its server installed attaches", () => {
  assert.deepEqual(decide("a.py", attempt("python"), STATES), { kind: "attach", language: "python", server: "basedpyright", idleS: 60 });
});

test("a TypeScript file whose server is not installed says so", () => {
  assert.deepEqual(decide("a.ts", attempt("typescript"), STATES), { kind: "show", found: { kind: "not-installed", language: "typescript", server: "typescript-language-server" } });
});

test("a JavaScript file goes to the TypeScript server", () => {
  assert.equal(decide("a.js", attempt("typescript"), STATES).kind, "show");
});

test("a Go file says that there is no server yet", () => {
  assert.deepEqual(decide("a.go", attempt("go"), STATES), { kind: "show", found: { kind: "no-server", language: "go" } });
});

test("a Markdown file works as it does without code intelligence", () => {
  assert.deepEqual(decide("notes.md", attempt("python"), STATES), { kind: "none" });
});

test("a file of another language than the attempt's is left alone", () => {
  assert.deepEqual(decide("a.ts", attempt("python"), STATES), { kind: "none" });
});

test("an attempt with no language, as an item has, is left alone", () => {
  assert.deepEqual(decide("a.py", attempt(null), STATES), { kind: "none" });
});

test("a language the list does not know is left alone", () => {
  assert.deepEqual(decide("a.rs", attempt("rust"), STATES), { kind: "none" });
});

test("a file that could have a server waits for the list", () => {
  assert.deepEqual(decide("a.py", attempt("python"), null), { kind: "waiting" });
});

test("a file that could not have one does not wait for the list", () => {
  assert.deepEqual(decide("notes.md", attempt("python"), null), { kind: "none" });
});

test("a file of a service project says code intelligence comes later, without the list", () => {
  assert.deepEqual(decide("src/server.ts", SERVICE_PROJECT, null), { kind: "show", found: { kind: "withheld", reason: "service_project" } });
});

test("a file of a service project never attaches, even with its server installed", () => {
  assert.deepEqual(decide("src/server.ts", SERVICE_PROJECT, INSTALLED_TYPESCRIPT), { kind: "show", found: { kind: "withheld", reason: "service_project" } });
});

test("a file of a service project that no server reads is left alone", () => {
  assert.deepEqual(decide("README.md", SERVICE_PROJECT, INSTALLED_TYPESCRIPT), { kind: "none" });
});

test("a Java file attaches to JDT LS once it is installed on a JDK it runs on", () => {
  assert.deepEqual(decide("Solution.java", attempt("java"), JAVA_INSTALLED), { kind: "attach", language: "java", server: "jdtls", idleS: 300 });
});

test("a Java file on a JDK JDT LS cannot run on shows why, with no session", () => {
  assert.deepEqual(decide("Solution.java", attempt("java"), JAVA_ON_JDK_21), {
    kind: "show",
    found: { kind: "needs-jdk", language: "java", detail: "needs JDK 25 or 26" },
  });
});
