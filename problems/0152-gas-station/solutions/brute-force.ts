export function canCompleteCircuit(gas: number[], cost: number[]): number {
  const n = gas.length;
  for (let start = 0; start < n; start++) {
    let fuel = 0;
    let step = 0;
    while (step < n) {
      const station = (start + step) % n;
      fuel += gas[station] - cost[station];
      if (fuel < 0) {
        break;
      }
      step++;
    }
    if (step === n) {
      return start;
    }
  }
  return -1;
}
