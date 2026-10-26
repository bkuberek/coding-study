const DURATIONS = [1, 7, 30];

export function mincostTickets(days: number[], costs: number[]): number {
  // A pass bought for days[index] covers through days[index] + duration - 1.
  const firstUncovered = (index: number, duration: number): number => {
    let following = index;
    while (following < days.length && days[following] < days[index] + duration) {
      following++;
    }
    return following;
  };
  // memo[index] is the cheapest cover of days[index..], or -1 when unknown.
  const memo = new Array<number>(days.length).fill(-1);
  const cheapestFrom = (index: number): number => {
    if (index === days.length) {
      return 0;
    }
    if (memo[index] === -1) {
      let best = Infinity;
      for (let pass = 0; pass < DURATIONS.length; pass++) {
        best = Math.min(best, costs[pass] + cheapestFrom(firstUncovered(index, DURATIONS[pass])));
      }
      memo[index] = best;
    }
    return memo[index];
  };
  return cheapestFrom(0);
}
