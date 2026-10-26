export function findMedianSortedArrays(nums1: number[], nums2: number[]): number {
  const [short, long] = nums1.length <= nums2.length ? [nums1, nums2] : [nums2, nums1];
  const total = short.length + long.length;
  const lowerSize = (total + 1) >> 1;
  let low = 0;
  let high = short.length;
  while (low <= high) {
    // Take `takeShort` values from `short` and the rest of the lower half from `long`.
    const takeShort = (low + high) >> 1;
    const takeLong = lowerSize - takeShort;
    const shortLeft = takeShort > 0 ? short[takeShort - 1] : -Infinity;
    const shortRight = takeShort < short.length ? short[takeShort] : Infinity;
    const longLeft = takeLong > 0 ? long[takeLong - 1] : -Infinity;
    const longRight = takeLong < long.length ? long[takeLong] : Infinity;
    if (shortLeft > longRight) {
      high = takeShort - 1;
    } else if (longLeft > shortRight) {
      low = takeShort + 1;
    } else {
      const lowerMax = Math.max(shortLeft, longLeft);
      return total % 2 === 1 ? lowerMax : (lowerMax + Math.min(shortRight, longRight)) / 2;
    }
  }
  throw new Error("the arrays must be sorted");
}
