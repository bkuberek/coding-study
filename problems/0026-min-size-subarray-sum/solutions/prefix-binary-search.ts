function lowerBound(values: number[], key: number, from: number): number {
  let low = from;
  let high = values.length;
  while (low < high) {
    const mid = (low + high) >>> 1;
    if (values[mid] < key) {
      low = mid + 1;
    } else {
      high = mid;
    }
  }
  return low;
}

export function minSubArrayLen(target: number, nums: number[]): number {
  const prefix = [0];
  for (const value of nums) {
    prefix.push(prefix[prefix.length - 1] + value);
  }
  let best = 0;
  for (let start = 0; start < nums.length; start++) {
    const end = lowerBound(prefix, prefix[start] + target, start + 1);
    if (end < prefix.length && (best === 0 || end - start < best)) {
      best = end - start;
    }
  }
  return best;
}
