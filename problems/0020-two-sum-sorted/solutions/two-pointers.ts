export function twoSumSorted(numbers: number[], target: number): number[] {
  let left = 0;
  let right = numbers.length - 1;
  while (left < right) {
    const total = numbers[left] + numbers[right];
    if (total === target) {
      return [left, right];
    }
    if (total < target) {
      left++;
    } else {
      right--;
    }
  }
  return [];
}
