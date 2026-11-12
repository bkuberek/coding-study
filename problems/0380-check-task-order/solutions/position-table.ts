export function isValidTaskOrder(n: number, prerequisites: number[][], order: number[]): boolean {
  if (order.length !== n) {
    return false;
  }
  // position[t]: where task t stands in the order, or -1 while it has not been seen.
  const position = new Array<number>(n).fill(-1);
  for (let place = 0; place < order.length; place++) {
    if (position[order[place]] !== -1) {
      return false;
    }
    position[order[place]] = place;
  }
  for (const [before, after] of prerequisites) {
    if (position[before] >= position[after]) {
      return false;
    }
  }
  return true;
}
