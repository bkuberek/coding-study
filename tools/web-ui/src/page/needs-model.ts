/**
 * What a problem depends on (docs/specs/service-projects.md#where-it-shows): the markers of the
 * Problems view, read from `cstudy list --json` alone, and whether a Start can go ahead.
 */

import type { NeedRow, Requires } from "./types.ts";

const DOCKER = "docker";

/** `docker`, then each backing service: what `cstudy list`'s NEEDS column says. */
export function needMarkers(requires: Requires | null): string[] {
  return requires === null ? [] : [DOCKER, ...requires.services];
}

/** The first requirement this machine does not meet, as the CLI words it; null when all are met. */
export function needsRefusal(rows: readonly NeedRow[]): string | null {
  return rows.find((row) => row.problem !== null)?.problem ?? null;
}
