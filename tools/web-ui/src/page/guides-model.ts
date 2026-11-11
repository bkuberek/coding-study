/**
 * What the Guides view (docs/specs/web-ui.md#guides-view) says of a path's steps, and how its
 * diagrams are drawn, apart from the page so the tests read it without a browser.
 */

import type { MermaidConfig } from "mermaid";

import { guideHash, problemHash } from "./routes.ts";
import type { PathStep, Theme } from "./types.ts";

/** The theme a diagram is drawn in: Mermaid's own light and dark, after the page's. */
export type DiagramTheme = "light" | "dark";

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

/** The page's theme, or the system's while the page follows it. */
export function diagramTheme(theme: Theme, systemDark: boolean): DiagramTheme {
  if (theme === "system") return systemDark ? "dark" : "light";
  return theme;
}

/** Mermaid draws text as SVG rather than HTML in a foreignObject, and leaves the width to the
 * page's stylesheet: both would otherwise set `style` attributes the page's CSP refuses. */
export function mermaidOptions(theme: DiagramTheme): MermaidConfig {
  const fixedWidth = { useMaxWidth: false };
  return {
    startOnLoad: false,
    securityLevel: "strict",
    // A diagram Mermaid cannot draw throws, and the view shows its text drawing instead.
    suppressErrorRendering: true,
    theme: theme === "dark" ? "dark" : "default",
    htmlLabels: false,
    flowchart: { ...fixedWidth, htmlLabels: false },
    sequence: fixedWidth,
    state: fixedWidth,
    class: fixedWidth,
    er: fixedWidth,
  };
}
