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
  event: string;
}

const MOVES = new Map<string, Move>([
  ["reserve", { from: null, to: "reserved", event: "rental.reserved" }],
  ["pickup", { from: "reserved", to: "out", event: "rental.picked_up" }],
  ["return", { from: "out", to: "returned", event: "rental.returned" }],
  ["cancel", { from: "reserved", to: "cancelled", event: "rental.cancelled" }],
]);

/** The state after `action`, or null when a rental in state `current` cannot make that move.
 * `current` is null for a rental that does not exist. */
export function nextState(action: string, current: RentalState | null): RentalState | null {
  const move = MOVES.get(action);
  return move !== undefined && move.from === current ? move.to : null;
}

/** The event type of an action that `nextState` allowed. */
export function eventType(action: string): string {
  return MOVES.get(action)?.event ?? "";
}
