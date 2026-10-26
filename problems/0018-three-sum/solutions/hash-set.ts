export function threeSum(nums: number[]): number[][] {
  const values = [...nums].sort((a, b) => a - b);
  const triples: number[][] = [];
  for (let i = 0; i < values.length - 2; i++) {
    if (i > 0 && values[i] === values[i - 1]) {
      continue;
    }
    const seen = new Set<number>();
    let lastLargest: number | undefined;
    for (let j = i + 1; j < values.length; j++) {
      const middle = -values[i] - values[j];
      if (seen.has(middle) && values[j] !== lastLargest) {
        triples.push([values[i], middle, values[j]]);
        lastLargest = values[j];
      }
      seen.add(values[j]);
    }
  }
  return triples;
}
