export function twoSum(nums: number[], target: number): number[] {
  const indexByValue = new Map<number, number>();
  for (let i = 0; i < nums.length; i++) {
    const partner = indexByValue.get(target - nums[i]);
    if (partner !== undefined) {
      return [partner, i];
    }
    indexByValue.set(nums[i], i);
  }
  return [];
}
