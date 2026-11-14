// The pipeline's state machine: the one place that knows which stage may follow which.

import type { Stage } from "../types.ts";

export const STAGES: readonly Stage[] = [
  "approved",
  "declined",
  "funded",
  "review",
  "submitted",
  "withdrawn",
];

const MOVES: Readonly<Record<Stage, readonly Stage[]>> = {
  submitted: ["review", "withdrawn"],
  review: ["approved", "declined", "withdrawn"],
  approved: ["funded", "withdrawn"],
  funded: [],
  declined: [],
  withdrawn: [],
};

export function canMove(from: Stage, to: Stage): boolean {
  return MOVES[from].includes(to);
}

export function isTerminal(stage: Stage): boolean {
  return MOVES[stage].length === 0;
}

/** Moves that say "this money goes out": they wait until every condition is cleared. */
export function needsClearedConditions(to: Stage): boolean {
  return to === "approved" || to === "funded";
}
