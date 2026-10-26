export function largestRectangleArea(heights: number[]): number {
  let best = 0;
  for (let left = 0; left < heights.length; left++) {
    // The tallest rectangle spanning bars left..right is as high as the lowest of them.
    let lowest = heights[left];
    for (let right = left; right < heights.length; right++) {
      lowest = Math.min(lowest, heights[right]);
      best = Math.max(best, lowest * (right - left + 1));
    }
  }
  return best;
}
