export function maxSubArray(nums: number[]): number {
  // The best subarray sum within nums[low..high] (inclusive).
  const bestIn = (low: number, high: number): number => {
    if (low === high) {
      return nums[low];
    }
    const middle = (low + high) >> 1;
    // The best crossing subarray is a best suffix of the left half plus a best prefix of the
    // right half.
    let leftSuffix = nums[middle];
    let total = 0;
    for (let i = middle; i >= low; i--) {
      total += nums[i];
      leftSuffix = Math.max(leftSuffix, total);
    }
    let rightPrefix = nums[middle + 1];
    total = 0;
    for (let i = middle + 1; i <= high; i++) {
      total += nums[i];
      rightPrefix = Math.max(rightPrefix, total);
    }
    return Math.max(bestIn(low, middle), bestIn(middle + 1, high), leftSuffix + rightPrefix);
  };
  return bestIn(0, nums.length - 1);
}
