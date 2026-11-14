function lowerBound(numbers: number[], key: number, from: number): number {
  let low = from;
  let high = numbers.length;
  while (low < high) {
    const mid = (low + high) >>> 1;
    if (numbers[mid] < key) {
      low = mid + 1;
    } else {
      high = mid;
    }
  }
  return low;
}

export function twoSumSorted(numbers: number[], target: number): number[] {
  for (let i = 0; i < numbers.length; i++) {
    const complement = target - numbers[i];
    const j = lowerBound(numbers, complement, i + 1);
    if (j < numbers.length && numbers[j] === complement) {
      return [i, j];
    }
  }
  return [];
}
