export function threeSum(nums: number[]): number[][] {
  const values = [...nums].sort((a, b) => a - b);
  const n = values.length;
  const triples: number[][] = [];
  for (let i = 0; i < n - 2 && values[i] <= 0; i++) {
    if (i > 0 && values[i] === values[i - 1]) {
      continue;
    }
    let left = i + 1;
    let right = n - 1;
    while (left < right) {
      const total = values[i] + values[left] + values[right];
      if (total < 0) {
        left++;
      } else if (total > 0) {
        right--;
      } else {
        triples.push([values[i], values[left], values[right]]);
        left++;
        right--;
        while (left < right && values[left] === values[left - 1]) {
          left++;
        }
      }
    }
  }
  return triples;
}
