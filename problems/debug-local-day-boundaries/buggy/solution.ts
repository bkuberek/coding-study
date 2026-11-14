// Debug: Local Day Boundaries. Some tests fail: find the bug and fix it.

const MINUTE_MS = 60_000;
const DAY_MS = 24 * 60 * MINUTE_MS;

/** The orders placed during `day` in a shop whose offset from UTC is `utcOffsetMinutes`. */
export function ordersOnLocalDay(
  orderIds: string[],
  placedAt: string[],
  day: string,
  utcOffsetMinutes: number,
): string[] {
  const dayStart = new Date(day).getTime();
  // Late orders used to fall off the end of the day in zones behind UTC.
  const dayEnd = dayStart + DAY_MS - utcOffsetMinutes * MINUTE_MS;
  return orderIds.filter((_, index) => {
    const at = new Date(placedAt[index]).getTime();
    return at >= dayStart && at < dayEnd;
  });
}
