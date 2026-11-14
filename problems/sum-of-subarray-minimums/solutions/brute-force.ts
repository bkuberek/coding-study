const MOD = 1_000_000_007;

export function sumSubarrayMins(arr: number[]): number {
  let total = 0;
  for (let start = 0; start < arr.length; start++) {
    let minimum = arr[start];
    for (let end = start; end < arr.length; end++) {
      minimum = Math.min(minimum, arr[end]);
      total += minimum;
    }
    // One start adds at most 3 * 10^4 * 3 * 10^4, so reducing once per start stays exact.
    total %= MOD;
  }
  return total;
}
