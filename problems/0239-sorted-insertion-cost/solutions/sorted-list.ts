const MODULUS = 1_000_000_007;

export function createSortedArray(instructions: number[]): number {
  const ordered: number[] = [];
  let cost = 0; // below 2^53 for every allowed input, so a number holds it exactly
  for (const value of instructions) {
    const less = firstIndexAtLeast(ordered, value);
    const lessOrEqual = firstIndexAbove(ordered, value);
    cost += Math.min(less, ordered.length - lessOrEqual);
    ordered.splice(lessOrEqual, 0, value);
  }
  return cost % MODULUS;
}

/** The number of values in the sorted list that are smaller than target. */
function firstIndexAtLeast(sorted: number[], target: number): number {
  let low = 0;
  let high = sorted.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (sorted[middle] < target) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }
  return low;
}

/** The number of values in the sorted list that are at most target. */
function firstIndexAbove(sorted: number[], target: number): number {
  let low = 0;
  let high = sorted.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (sorted[middle] <= target) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }
  return low;
}
