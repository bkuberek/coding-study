// What a rental is, and which moves it can make. Nothing here knows about storage.

export type RentalState = "reserved" | "out" | "returned" | "cancelled";

export interface Rental {
  id: string;
  state: RentalState;
  version: number;
}

interface Move {
  from: RentalState | null;
  to: RentalState;
}

const MOVES = new Map<string, Move>([
  ["reserve", { from: null, to: "reserved" }],
  ["pickup", { from: "reserved", to: "out" }],
  ["return", { from: "out", to: "returned" }],
  ["cancel", { from: "reserved", to: "cancelled" }],
]);

/** The state after `action`, or null when a rental in state `current` cannot make that move.
 * `current` is null for a rental that does not exist. */
export function nextState(action: string, current: RentalState | null): RentalState | null {
  const move = MOVES.get(action);
  return move !== undefined && move.from === current ? move.to : null;
}
