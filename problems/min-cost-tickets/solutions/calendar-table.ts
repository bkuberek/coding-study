export function mincostTickets(days: number[], costs: number[]): number {
  const lastDay = days[days.length - 1];
  const travel = new Set(days);
  // cost[d] is the cheapest way to cover every trip on calendar days 1..d.
  const cost = new Array<number>(lastDay + 1).fill(0);
  for (let d = 1; d <= lastDay; d++) {
    if (!travel.has(d)) {
      cost[d] = cost[d - 1];
      continue;
    }
    cost[d] = Math.min(
      cost[d - 1] + costs[0],
      cost[Math.max(0, d - 7)] + costs[1],
      cost[Math.max(0, d - 30)] + costs[2],
    );
  }
  return cost[lastDay];
}
