/** The loading, empty and error states every view shows (docs/specs/web-ui.md#page). */

import { ApiError } from "./api.ts";
import { command, h } from "./dom.ts";

export function loading(text = "loading…"): HTMLElement {
  return h("p", { class: "state state-loading", role: "status" }, h("span", { class: "spinner", "aria-hidden": "true" }), text);
}

export function empty(text: string, ...more: Node[]): HTMLElement {
  return h("div", { class: "state state-empty" }, h("p", {}, text), ...more);
}

/** The text of a refusal, as the CLI words it. */
export function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** An error as the CLI words it; an environment error adds its `fix` and a way to the Health view. */
export function failure(error: unknown): HTMLElement {
  const known = error instanceof ApiError ? error : null;
  const message = messageOf(error);
  return h(
    "div",
    { class: "state state-error", role: "alert" },
    h("p", { class: "state-title" }, h("span", { class: "glyph", "aria-hidden": "true" }, "✕ "), "error: ", message),
    known?.fix ? h("p", {}, "fix: ", command(known.fix)) : null,
    known?.code === "environment" ? h("p", {}, h("a", { href: "#/health" }, "Check the workspace in the Health view")) : null,
  );
}

/** Shows `error` in place of a region that failed to load. */
export function showFailure(region: Element, error: unknown): void {
  region.replaceChildren(failure(error));
}
