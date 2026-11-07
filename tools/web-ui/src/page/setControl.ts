/**
 * The add-to-set control of the Problems and Problem views (docs/specs/web-ui.md#sets-view): a
 * button that reads the sets a problem is in. It opens the dialog, in the dialogs' chunk.
 */

import type { PageContext } from "./context.ts";
import { h } from "./dom.ts";
import { openLazily } from "./lazy.ts";
import type { SetSummary } from "./types.ts";

export function setsHolding(sets: readonly SetSummary[], slug: string): string[] {
  return sets.filter((found) => found.slugs.includes(slug)).map((found) => found.name);
}

export function membershipLabel(names: readonly string[]): string {
  const [first, ...others] = names;
  if (first === undefined) return "+ set";
  return others.length ? `${first} +${others.length}` : first;
}

export function membershipWords(slug: string, names: readonly string[]): string {
  if (names.length === 0) return `${slug} is in no set: add it to one`;
  const last = names[names.length - 1];
  const listed = names.length === 1 ? last : `${names.slice(0, -1).join(", ")} and ${last}`;
  return `${slug} is in ${listed}: change its sets`;
}

export interface SetControlOptions {
  readonly held: readonly string[];
  /** Hears what the problem is in, once the dialog closes. */
  readonly closed?: (names: readonly string[]) => void;
  /** Its words where the sets are listed beside it; otherwise it reads them itself. */
  readonly label?: string;
}

export function setControl(context: PageContext, slug: string, options: SetControlOptions): HTMLElement {
  const button = h("button", { type: "button", class: options.label ? "button set-control" : "ghost set-control" });
  const show = (names: readonly string[]) => {
    button.textContent = options.label ?? membershipLabel(names);
    button.title = membershipWords(slug, names);
    button.setAttribute("aria-label", button.title);
  };
  show(options.held);
  button.addEventListener("click", () => {
    openLazily(context, () => import("./sheets.ts"), (sheets) => {
      void sheets.openSetMembership(context, slug, show).then((names) => options.closed?.(names));
    });
  });
  return button;
}
