// One answer from any number of vendors, none of which can take another with it.

import type { RoomSource, Slot } from "./vendors/roomSource.ts";

export type RoomAvailability = { slots: Slot[]; unavailable: string[] };

function byStartThenRoom(first: Slot, second: Slot): number {
  const key = (slot: Slot) => `${slot.start} ${slot.room}`;
  return key(first) < key(second) ? -1 : key(first) > key(second) ? 1 : 0;
}

export async function roomAvailability(
  date: string,
  vendors: readonly RoomSource[],
): Promise<RoomAvailability> {
  const answers = await Promise.allSettled(vendors.map((vendor) => vendor.openSlots(date)));
  const slots: Slot[] = [];
  const unavailable: string[] = [];
  answers.forEach((answer, index) => {
    if (answer.status === "fulfilled") {
      slots.push(...answer.value);
    } else {
      unavailable.push(vendors[index]!.name);
    }
  });
  return { slots: slots.sort(byStartThenRoom), unavailable: unavailable.sort() };
}
