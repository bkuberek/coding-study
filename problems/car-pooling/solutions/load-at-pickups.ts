export function carPooling(trips: number[][], capacity: number): boolean {
  // The load is highest right after some pickup, so checking every pickup point suffices.
  let busiest = 0;
  for (const [, pickup] of trips) {
    let load = 0;
    for (const [passengers, start, end] of trips) {
      if (start <= pickup && pickup < end) {
        load += passengers;
      }
    }
    busiest = Math.max(busiest, load);
  }
  return busiest <= capacity;
}
