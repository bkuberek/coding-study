export function countSmaller(nums: number[]): number[] {
  // Coordinate compression: rank 1 is the smallest distinct value.
  const distinct = [...new Set(nums)].sort((a, b) => a - b);
  const rank = new Map<number, number>();
  distinct.forEach((value, position) => rank.set(value, position + 1));
  const size = distinct.length;
  const tree = new Int32Array(size + 1); // how many seen values have each rank
  const counts = new Array<number>(nums.length);
  for (let i = nums.length - 1; i >= 0; i--) {
    let r = rank.get(nums[i])!;
    // Seen values with a rank below r, i.e. strictly smaller values to the right.
    let smaller = 0;
    for (let j = r - 1; j > 0; j -= j & -j) {
      smaller += tree[j];
    }
    counts[i] = smaller;
    for (; r <= size; r += r & -r) {
      tree[r]++;
    }
  }
  return counts;
}
