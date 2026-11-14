export function carPooling(trips: number[][], capacity: number): boolean {
  let last = 0;
  for (const trip of trips) {
    last = Math.max(last, trip[2]);
  }
  // change[x] is how much the load changes at location x; its prefix sums are the loads.
  const change = new Int32Array(last + 1);
  for (const [passengers, start, end] of trips) {
    change[start] += passengers;
    change[end] -= passengers;
  }
  let load = 0;
  for (const delta of change) {
    load += delta;
    if (load > capacity) {
      return false;
    }
  }
  return true;
}
