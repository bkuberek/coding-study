export function isValidTaskOrder(n: number, prerequisites: number[][], order: number[]): boolean {
  if (order.length !== n) {
    return false;
  }
  for (let task = 0; task < n; task++) {
    if (order.filter((listed) => listed === task).length !== 1) {
      return false;
    }
  }
  for (const [before, after] of prerequisites) {
    if (order.indexOf(before) >= order.indexOf(after)) {
      return false;
    }
  }
  return true;
}
