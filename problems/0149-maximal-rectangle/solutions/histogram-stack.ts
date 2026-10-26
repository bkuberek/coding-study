function largestInHistogram(heights: Int32Array, rising: Int32Array): number {
  let best = 0;
  // rising[0 .. size) holds indexes of bars whose heights strictly increase from bottom to top.
  let size = 0;
  // One extra bar of height 0 at the end pops every bar still waiting.
  for (let index = 0; index <= heights.length; index++) {
    const height = index < heights.length ? heights[index] : 0;
    while (size > 0 && heights[rising[size - 1]] >= height) {
      const top = rising[--size];
      const left = size > 0 ? rising[size - 1] : -1;
      best = Math.max(best, heights[top] * (index - left - 1));
    }
    rising[size++] = index;
  }
  return best;
}

export function maximalRectangle(matrix: string[][]): number {
  const columns = matrix[0].length;
  // heights[c] counts the consecutive ones in column c ending at the current row.
  const heights = new Int32Array(columns);
  const rising = new Int32Array(columns + 1);
  let best = 0;
  for (const row of matrix) {
    for (let c = 0; c < columns; c++) {
      heights[c] = row[c] === "1" ? heights[c] + 1 : 0;
    }
    best = Math.max(best, largestInHistogram(heights, rising));
  }
  return best;
}
