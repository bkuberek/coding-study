import assert from "node:assert/strict";
import { test } from "node:test";

import { diagnosticPath, diagnosticsByPath } from "../src/page/run-diagnostics.ts";
import type { Diagnostic } from "../src/page/run-events.ts";

function diagnostic(file: string | null, line: number | null = 3): Diagnostic {
  return { type: "diagnostic", source: "load", severity: "error", file, line, column: null, code: "SyntaxError", message: "invalid syntax" };
}

test("a project's diagnostic names a file of the tree as it is", () => {
  assert.equal(diagnosticPath("bank/bank.py", "project", "projects/bank"), "bank/bank.py");
});

test("a single-file diagnostic loses the attempt's root", () => {
  assert.equal(diagnosticPath("python/practice/two_sum.py", "function", "python/practice"), "two_sum.py");
});

test("a diagnostic outside the attempt's root names no file of the tree", () => {
  assert.equal(diagnosticPath("typescript/support.ts", "function", "python/practice"), null);
});

test("a diagnostic without a file names none", () => {
  assert.equal(diagnosticPath(null, "project", "projects/bank"), null);
});

test("diagnostics group by the file they mark", () => {
  const grouped = diagnosticsByPath([diagnostic("bank/a.py", 1), diagnostic("bank/a.py", 5), diagnostic("bank/b.py")], "project", "projects/bank");
  assert.deepEqual([...grouped].map(([path, found]) => [path, found.map((one) => one.line)]), [["bank/a.py", [1, 5]], ["bank/b.py", [3]]]);
});

test("a diagnostic with no file of the tree marks no file", () => {
  assert.equal(diagnosticsByPath([diagnostic(null)], "project", "projects/bank").size, 0);
});
