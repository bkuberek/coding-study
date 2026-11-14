export function largestRectangleArea(heights: number[]): number {
  let best = 0;
  // Indexes of bars whose heights strictly increase from bottom to top.
  const rising: number[] = [];
  // One extra bar of height 0 at the end pops every bar still waiting.
  for (let index = 0; index <= heights.length; index++) {
    const height = index < heights.length ? heights[index] : 0;
    while (rising.length > 0 && heights[rising[rising.length - 1]] >= height) {
      const top = rising.pop()!;
      // The bar below `top` on the stack is lower, and so is `index` (or it is equal and
      // a later pop covers the full width): the rectangle spans the bars between them.
      const left = rising.length > 0 ? rising[rising.length - 1] : -1;
      best = Math.max(best, heights[top] * (index - left - 1));
    }
    rising.push(index);
  }
  return best;
}
