/**
 * The Solution button (docs/specs/web-ui.md#solutions); the pane it opens is in `solutionPane.ts`,
 * fetched on first use.
 */

import type { PageContext } from "./context.ts";
import { h } from "./dom.ts";
import { openLazily } from "./lazy.ts";

export const SOLUTION_COMMAND = "cstudy solution";

/** The Solution button: opens the pane, and is disabled with the lock message during a mock. */
export function solutionButton(context: PageContext, slug: string): HTMLButtonElement {
  const button = h("button", { type: "button", class: "button" }, "Solution…");
  button.addEventListener("click", () => openLazily(context, () => import("./sheets.ts"), (pane) => pane.openSolution(context, slug)));
  context.mock.follow(SOLUTION_COMMAND, button, (lock) => {
    button.disabled = lock !== null;
    button.title = lock ?? `${SOLUTION_COMMAND} ${slug}: the reference, behind its question`;
    if (lock === null) button.removeAttribute("aria-description");
    else button.setAttribute("aria-description", lock);
  });
  return button;
}
