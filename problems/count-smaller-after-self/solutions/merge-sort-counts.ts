export function countSmaller(nums: number[]): number[] {
  const n = nums.length;
  const counts = new Array<number>(n).fill(0);
  let order = Int32Array.from({ length: n }, (_, i) => i); // positions, sorted by value per run
  let buffer = new Int32Array(n);
  // Bottom-up merge sort of positions by value; no recursion needed.
  for (let width = 1; width < n; width *= 2) {
    for (let low = 0; low < n; low += 2 * width) {
      const middle = Math.min(low + width, n);
      const high = Math.min(low + 2 * width, n);
      let left = low;
      let right = middle;
      let out = low;
      while (left < middle) {
        if (right < high && nums[order[right]] < nums[order[left]]) {
          buffer[out++] = order[right++];
        } else {
          // Every right-half element taken so far is smaller and came after it.
          counts[order[left]] += right - middle;
          buffer[out++] = order[left++];
        }
      }
      while (right < high) {
        buffer[out++] = order[right++];
      }
    }
    [order, buffer] = [buffer, order];
  }
  return counts;
}
