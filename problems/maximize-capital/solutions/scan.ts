export function findMaximizedCapital(k: number, w: number, profits: number[], capital: number[]): number {
  const used = new Array<boolean>(profits.length).fill(false);
  let funds = w;
  for (let round = 0; round < k; round++) {
    let best = -1;
    for (let index = 0; index < profits.length; index++) {
      if (!used[index] && capital[index] <= funds && (best < 0 || profits[index] > profits[best])) {
        best = index;
      }
    }
    if (best < 0) {
      break; // nothing affordable now, and capital cannot grow any more
    }
    used[best] = true;
    funds += profits[best];
  }
  return funds;
}
