export function findCheapestPrice(n: number, flights: number[][], src: number, dst: number, k: number): number {
  // price[c] is the cheapest known price to reach c with at most `round` flights.
  let price = new Array<number>(n).fill(Infinity);
  price[src] = 0;
  for (let round = 0; round <= k; round++) {
    // Read from the previous round only, so one round never chains two flights.
    const previous = price;
    price = previous.slice();
    let changed = false;
    for (const [start, end, cost] of flights) {
      if (previous[start] + cost < price[end]) {
        price[end] = previous[start] + cost;
        changed = true;
      }
    }
    if (!changed) break;
  }
  return price[dst] === Infinity ? -1 : price[dst];
}
