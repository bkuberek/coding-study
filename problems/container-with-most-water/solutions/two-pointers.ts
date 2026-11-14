export function maxArea(height: number[]): number {
  let left = 0;
  let right = height.length - 1;
  let best = 0;
  while (left < right) {
    const width = right - left;
    if (height[left] < height[right]) {
      best = Math.max(best, width * height[left]);
      left++;
    } else {
      best = Math.max(best, width * height[right]);
      right--;
    }
  }
  return best;
}
