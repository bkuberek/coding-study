/**
 * How the results panel words a row, as the terminal report does (docs/specs/cli.md#cstudy-test):
 * durations, inputs by name, the facts beside a case, and what a failing case shows below it.
 */

import type { CaseRow } from "./results-model.ts";
import type { CaseResult, LevelResult, StressResult, TestResult } from "./run-events.ts";

const NS_PER_MS = 1_000_000;
const MS_PER_S = 1000;
const FINE_MS = 10;

/** `0.04ms`, `412ms`, `2.6s`. */
export function durationText(nanoseconds: number): string {
  return millisecondsText(nanoseconds / NS_PER_MS);
}

export function millisecondsText(milliseconds: number): string {
  if (milliseconds >= MS_PER_S) return `${(milliseconds / MS_PER_S).toFixed(1)}s`;
  if (milliseconds >= FINE_MS) return `${Math.round(milliseconds)}ms`;
  return `${milliseconds.toFixed(2)}ms`;
}

/** A value in the report's JSON, with a space after each comma. */
export function valueText(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(valueText).join(", ")}]`;
  if (value !== null && typeof value === "object") {
    const fields = Object.entries(value as Record<string, unknown>).map(([name, field]) => `${JSON.stringify(name)}: ${valueText(field)}`);
    return `{${fields.join(", ")}}`;
  }
  return JSON.stringify(value) ?? "null";
}

/** `nums=[-3, 8, 0, 3]  target=0`, or `ops [...]  args [...]` for a design problem. */
export function inputText(input: unknown): string {
  if (input === null || typeof input !== "object" || Array.isArray(input)) return valueText(input);
  const fields = Object.entries(input as Record<string, unknown>);
  if (fields.some(([name]) => name === "ops")) return fields.map(([name, value]) => `${name} ${valueText(value)}`).join("  ");
  return fields.map(([name, value]) => `${name}=${valueText(value)}`).join("  ");
}

/** What the report prints beside a case: `hidden · level 2 · 0.04ms`, the size of an oracle input, a time-limit verdict. */
export function caseFacts(row: CaseRow): string {
  if (row.oracle) return `oracle · n=${row.n ?? "?"}`;
  const facts = [row.visible ? null : "hidden", row.level === null ? null : `level ${row.level}`];
  const result = row.result;
  if (result?.status === "tle" && result.time_limit_ms !== undefined) {
    const basis = result.time_limit_basis ? ` (${result.time_limit_basis})` : "";
    facts.push(`${durationText(result.duration_ns)} > limit ${millisecondsText(result.time_limit_ms)}${basis}`);
  } else if (result) {
    facts.push(durationText(result.duration_ns));
  }
  return facts.filter((fact) => fact !== null).join(" · ");
}

/** The lines below a case that did not pass, each a label and its text. */
export function caseLines(result: CaseResult | TestResult | null): [string, string][] {
  if (!result || result.status === "pass") return [];
  const lines: [string, string][] = [];
  const add = (label: string, text: string | null | undefined) => {
    if (text) lines.push([label, text]);
  };
  if ("message" in result) add("message", result.message);
  if ("input" in result && result.input !== undefined) add("input", inputText(result.input));
  if (result.expected !== undefined) add("expected", valueText(result.expected));
  if (result.actual !== undefined) add("actual", valueText(result.actual));
  if ("reason" in result) add("reason", result.reason);
  if (result.error) {
    add("error", result.error.message ? `${result.error.type}: ${result.error.message}` : result.error.type);
    add("trace", result.error.trace);
  }
  if ("hang_guard_ms" in result && result.hang_guard_ms !== undefined) add("hang guard", millisecondsText(result.hang_guard_ms));
  if ("exit_code" in result && result.exit_code !== undefined) add("exit code", String(result.exit_code));
  if ("stderr" in result) add("stderr", result.stderr);
  add("stdout", result.stdout);
  if ("note" in result) add("note", result.note);
  return lines;
}

/** `virtual · 1/3 runs passed · median 38ms`. */
export function stressFacts(variant: string, result: Pick<StressResult, "runs" | "runs_passed" | "median_ms"> | null): string {
  if (!result) return variant;
  const median = result.median_ms === null ? [] : [`median ${millisecondsText(result.median_ms)}`];
  return [variant, `${result.runs_passed}/${result.runs} runs passed`, ...median].join(" · ");
}

/** `4/5 (2 visible, 3 hidden)`; a mock submission counts its failing hidden cases, which it never shows. */
export function levelLine(level: LevelResult, mock: boolean): string {
  const line = `${level.passed}/${level.total} (${level.visible_total} visible, ${level.hidden_total} hidden)`;
  const failedHidden = level.hidden_total - level.hidden_passed;
  if (!mock || failedHidden === 0) return line;
  return `${line} · ${failedHidden} hidden ${failedHidden === 1 ? "case" : "cases"} failed`;
}

/** `TestBank::test_ex1` of `tests/test_level_1.py::TestBank::test_ex1`. */
export function testName(id: string): string {
  const at = id.indexOf("::");
  return at < 0 ? id : id.slice(at + 2);
}
