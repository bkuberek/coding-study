export function threeSum(nums: number[]): number[][] {
  const values = [...nums].sort((a, b) => a - b);
  const n = values.length;
  const triples: number[][] = [];
  for (let i = 0; i < n - 2; i++) {
    if (i > 0 && values[i] === values[i - 1]) {
      continue;
    }
    for (let j = i + 1; j < n - 1; j++) {
      if (j > i + 1 && values[j] === values[j - 1]) {
        continue;
      }
      const third = -values[i] - values[j];
      for (let k = j + 1; k < n; k++) {
        if (values[k] === third) {
          triples.push([values[i], values[j], third]);
          break;
        }
      }
    }
  }
  return triples;
}
