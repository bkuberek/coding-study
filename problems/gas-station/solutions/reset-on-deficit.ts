export function canCompleteCircuit(gas: number[], cost: number[]): number {
  let total = 0; // fuel balance of the whole circle
  let fuel = 0; // fuel since the current candidate start
  let start = 0;
  for (let station = 0; station < gas.length; station++) {
    const surplus = gas[station] - cost[station];
    total += surplus;
    fuel += surplus;
    if (fuel < 0) {
      // No station from `start` to `station` can be the answer; try the next one.
      start = station + 1;
      fuel = 0;
    }
  }
  return total >= 0 ? start : -1;
}
