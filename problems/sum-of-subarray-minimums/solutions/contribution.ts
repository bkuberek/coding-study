const MOD = 1_000_000_007;

export function sumSubarrayMins(arr: number[]): number {
  let total = 0;
  // Indexes whose values strictly increase from bottom to top.
  const stack: number[] = [];
  // One extra step with value 0, below every element, pops whatever is left.
  for (let index = 0; index <= arr.length; index++) {
    const value = index < arr.length ? arr[index] : 0;
    while (stack.length > 0 && arr[stack[stack.length - 1]] >= value) {
      const middle = stack.pop()!;
      // Starts after the previous strictly smaller element, ends before the next
      // smaller-or-equal one (index): arr[middle] is the minimum of left * right subarrays.
      const left = middle - (stack.length > 0 ? stack[stack.length - 1] : -1);
      const right = index - middle;
      // At most 3 * 10^4 * (3 * 10^4)^2 / 4, far below 2^53, so the product is exact.
      total = (total + arr[middle] * left * right) % MOD;
    }
    stack.push(index);
  }
  return total;
}
