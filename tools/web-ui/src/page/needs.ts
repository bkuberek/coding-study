/**
 * What a service project depends on, drawn in the Problem view, the Start dialog and the Attempt
 * view (docs/specs/service-projects.md#where-it-shows): the rows `cstudy show` lists, each with its
 * state on this machine. Reading them asks Docker and starts nothing.
 */

import "./needs.css";

import type { PageContext } from "./context.ts";
import { badge, fixHint, h } from "./dom.ts";
import type { NeedRow } from "./types.ts";

/** `GET /api/v1/problems/{slug}/needs`; null for a problem that is not a service project. */
export async function readNeeds(context: PageContext, slug: string): Promise<readonly NeedRow[] | null> {
  const document = await context.api.get<{ readonly needs: readonly NeedRow[] | null }>(`/api/v1/problems/${encodeURIComponent(slug)}/needs`);
  return document.needs;
}

/** `docker  running engine and compose v2`, and under a requirement not met here, why, in the CLI's words. */
export function needsList(rows: readonly NeedRow[]): HTMLElement {
  return h(
    "dl",
    { class: "needs-list" },
    ...rows.flatMap((row) => [
      h("dt", {}, row.label),
      h("dd", {}, row.text, row.problem === null ? null : h("span", { class: "need-problem" }, badge("!", "not met here", "warn"), " ", fixHint(row.problem))),
    ]),
  );
}
