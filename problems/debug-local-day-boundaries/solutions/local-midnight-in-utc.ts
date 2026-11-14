const MINUTE_MS = 60_000;
const DAY_MS = 24 * 60 * MINUTE_MS;

/** The orders placed during `day` in a shop whose offset from UTC is `utcOffsetMinutes`. */
export function ordersOnLocalDay(
  orderIds: string[],
  placedAt: string[],
  day: string,
  utcOffsetMinutes: number,
): string[] {
  // A date-only string parses as midnight UTC. Local midnight comes `offset` earlier than that:
  // nine hours ahead of UTC, midnight has already happened nine hours before midnight UTC.
  const dayStart = Date.parse(day) - utcOffsetMinutes * MINUTE_MS;
  const dayEnd = dayStart + DAY_MS;
  return orderIds.filter((_, index) => {
    const at = Date.parse(placedAt[index]);
    return at >= dayStart && at < dayEnd;
  });
}
