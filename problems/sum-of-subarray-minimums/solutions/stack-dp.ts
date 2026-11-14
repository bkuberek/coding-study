const MOD = 1_000_000_007;

export function sumSubarrayMins(arr: number[]): number {
  // ending[i] is the sum of the minimums of the subarrays that end at i (at most 9 * 10^8).
  const ending = new Array<number>(arr.length).fill(0);
  // Indexes whose values strictly increase from bottom to top.
  const stack: number[] = [];
  let total = 0;
  for (let index = 0; index < arr.length; index++) {
    const value = arr[index];
    while (stack.length > 0 && arr[stack[stack.length - 1]] >= value) {
      stack.pop();
    }
    if (stack.length > 0) {
      const previous = stack[stack.length - 1];
      // Starts after the previous smaller element have minimum `value`; earlier starts
      // have the same minimums as the subarrays ending at `previous`.
      ending[index] = ending[previous] + value * (index - previous);
    } else {
      ending[index] = value * (index + 1);
    }
    stack.push(index);
    total = (total + ending[index]) % MOD;
  }
  return total;
}
