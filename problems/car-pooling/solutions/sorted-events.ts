export function carPooling(trips: number[][], capacity: number): boolean {
  const events: [number, number][] = [];
  for (const [passengers, start, end] of trips) {
    events.push([start, passengers], [end, -passengers]);
  }
  // By location, then by change: drop-offs (negative) come before pickups at the same place.
  events.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  let load = 0;
  for (const [, change] of events) {
    load += change;
    if (load > capacity) {
      return false;
    }
  }
  return true;
}
