/**
 * What the Guides view (docs/specs/web-ui.md#guides-view) says of a path's steps, apart from the
 * page so the tests read it without a browser.
 */

import { guideHash, problemHash } from "./routes.ts";
import type { PathStep } from "./types.ts";

export function stepHref(step: PathStep): string {
  return step.kind === "guide" ? guideHash(step.slug) : problemHash(step.slug);
}

/** The command `cstudy learn --path` names for the step. */
export function stepCommand(step: PathStep): string {
  return step.kind === "guide" ? `cstudy learn ${step.slug}` : `cstudy start ${step.slug}`;
}

/** What a level target asks: the step is done once that level passes. */
export function stepTarget(step: PathStep): string {
  return step.level === null ? "" : `through level ${step.level}`;
}

export function progressText(done: number, total: number): string {
  return `${done} of ${total} steps done`;
}
