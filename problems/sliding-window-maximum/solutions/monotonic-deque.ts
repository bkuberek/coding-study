export function maxSlidingWindow(nums: number[], k: number): number[] {
  const candidates = new Int32Array(nums.length);
  let head = 0;
  let tail = 0;
  const maxima: number[] = [];
  for (let right = 0; right < nums.length; right++) {
    while (tail > head && nums[candidates[tail - 1]] <= nums[right]) {
      tail--;
    }
    candidates[tail++] = right;
    if (candidates[head] <= right - k) {
      head++;
    }
    if (right >= k - 1) {
      maxima.push(nums[candidates[head]]);
    }
  }
  return maxima;
}
