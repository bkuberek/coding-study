// Turns a thrown value into the protocol's `error` object: type, message, and a trace filtered
// to user frames (docs/specs/runners.md#event-stream---out-json-lines).

import { basename } from "node:path";
import { fileURLToPath } from "node:url";
import type { ErrorInfo } from "./protocol.ts";

const MAX_TRACE_LINES = 10;
const RUNNER_DIRECTORY_URL = new URL("..", import.meta.url).href;
const FRAME = /^\s*at (?:(.*?) \()?(.+?):(\d+):\d+\)?$/;
const SYNTAX_LOCATION = /^(file:\S+):(\d+)$/;

export function describeThrown(thrown: unknown): ErrorInfo {
  if (!isErrorLike(thrown)) {
    return { type: typeof thrown, message: String(thrown) };
  }
  const trace = userTrace(thrown.stack);
  const info = { type: errorType(thrown), message: thrown.message };
  return trace === "" ? info : { ...info, trace };
}

interface ErrorLike {
  readonly message: string;
  readonly name?: unknown;
  readonly stack?: unknown;
}

function isErrorLike(value: unknown): value is ErrorLike {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as ErrorLike).message === "string"
  );
}

/** The class name (`TypeError`, a user's `class QueueEmpty extends Error`), else `name`. */
function errorType(error: ErrorLike): string {
  const className = (error as object).constructor?.name;
  if (
    typeof className === "string" &&
    className !== "" &&
    className !== "Object"
  ) {
    return className;
  }
  return typeof error.name === "string" && error.name !== ""
    ? error.name
    : "Error";
}

/** Frames from user files only (not node internals or this runner), as `file.ts:7 in fn`. */
function userTrace(stack: unknown): string {
  if (typeof stack !== "string") {
    return "";
  }
  const lines = stack.split("\n");
  const frames = lines.map(userFrame).filter((frame) => frame !== null);
  return [...syntaxExcerpt(lines), ...frames]
    .slice(0, MAX_TRACE_LINES)
    .join("\n");
}

/**
 * A syntax error's stack starts with `file:///…/user.ts:2` and the offending source lines, up to
 * a blank line; keep them as `user.ts:2` plus the excerpt.
 */
function syntaxExcerpt(lines: readonly string[]): string[] {
  const match = SYNTAX_LOCATION.exec(lines[0] ?? "");
  const [, location = "", lineNumber] = match ?? [];
  if (match === null || !isUserLocation(location)) {
    return [];
  }
  const end = lines.indexOf("", 1);
  return [
    `${basename(fileURLToPath(location))}:${lineNumber}`,
    ...lines.slice(1, end < 0 ? 1 : end),
  ];
}

function userFrame(line: string): string | null {
  const match = FRAME.exec(line);
  if (match === null) {
    return null;
  }
  const [, functionName, location = "", lineNumber] = match;
  if (!isUserLocation(location)) {
    return null;
  }
  const file = basename(
    location.startsWith("file:") ? fileURLToPath(location) : location,
  );
  return functionName === undefined
    ? `${file}:${lineNumber}`
    : `${file}:${lineNumber} in ${functionName}`;
}

function isUserLocation(location: string): boolean {
  return (
    location.startsWith("file:") && !location.startsWith(RUNNER_DIRECTORY_URL)
  );
}
