export function lengthOfLIS(nums: number[]): number {
  // tails[L - 1] is the smallest last value of any increasing subsequence of length L seen
  // so far; it is strictly increasing, so it can be binary searched.
  const tails: number[] = [];
  for (const value of nums) {
    // Lower bound: the first position whose tail is >= value.
    let low = 0;
    let high = tails.length;
    while (low < high) {
      const middle = (low + high) >> 1;
      if (tails[middle] < value) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    tails[low] = value;
  }
  return tails.length;
}
