const WINDOW = 30;

export function mincostTickets(days: number[], costs: number[]): number {
  // cost[d % WINDOW] holds the cheapest cover of days 1..d for the last 30 calendar days;
  // nothing older is ever read, because the longest pass lasts 30 days.
  const cost = new Array<number>(WINDOW).fill(0);
  const lastDay = days[days.length - 1];
  let nextTrip = 0;
  for (let d = 1; d <= lastDay; d++) {
    const previous = cost[(d - 1) % WINDOW];
    if (d !== days[nextTrip]) {
      cost[d % WINDOW] = previous;
      continue;
    }
    nextTrip++;
    const weekAgo = d >= 7 ? cost[(d - 7) % WINDOW] : 0;
    const monthAgo = d >= WINDOW ? cost[d % WINDOW] : 0;
    cost[d % WINDOW] = Math.min(previous + costs[0], weekAgo + costs[1], monthAgo + costs[2]);
  }
  return cost[lastDay % WINDOW];
}
