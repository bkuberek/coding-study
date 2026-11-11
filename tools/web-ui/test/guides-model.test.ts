import assert from "node:assert/strict";
import { test } from "node:test";

import { diagramTheme, mermaidOptions, progressText, stepCommand, stepHref, stepTarget } from "../src/page/guides-model.ts";
import type { PathStep } from "../src/page/types.ts";

function step(kind: PathStep["kind"], slug: string, level: number | null = null): PathStep {
  return { position: 1, kind, slug, title: slug, level, done: false, status: "new", level_passed: null };
}

test("a guide step opens the guide, a problem step the problem", () => {
  assert.deepEqual([stepHref(step("guide", "hash-functions")), stepHref(step("problem", "two-sum"))], ["#/guides/hash-functions", "#/problems/two-sum"]);
});

test("a step names the command the terminal runs for it, as cstudy learn --path does", () => {
  assert.deepEqual([stepCommand(step("guide", "hash-functions")), stepCommand(step("problem", "two-sum"))], ["cstudy learn hash-functions", "cstudy start two-sum"]);
});

test("a level target reads as the level to pass; no target reads as nothing", () => {
  assert.deepEqual([stepTarget(step("problem", "tamper-evident-ledger", 2)), stepTarget(step("problem", "two-sum"))], ["through level 2", ""]);
});

test("a path's progress reads as steps done of all", () => {
  assert.equal(progressText(3, 21), "3 of 21 steps done");
});

test("diagrams follow the page's theme, and the system's when the page follows it", () => {
  assert.deepEqual(
    [diagramTheme("dark", false), diagramTheme("light", true), diagramTheme("system", true), diagramTheme("system", false)],
    ["dark", "light", "dark", "light"],
  );
});

test("Mermaid draws with the theme, strict security, SVG labels and no width of its own", () => {
  const options = mermaidOptions("dark");
  assert.deepEqual(
    [options.theme, options.securityLevel, options.startOnLoad, options.htmlLabels, options.flowchart?.htmlLabels, options.flowchart?.useMaxWidth],
    ["dark", "strict", false, false, false, false],
  );
  assert.equal(mermaidOptions("light").theme, "default");
});
