export function findMedianSortedArrays(nums1: number[], nums2: number[]): number {
  const merged = [...nums1, ...nums2].sort((a, b) => a - b);
  const middle = merged.length >> 1;
  if (merged.length % 2 === 1) {
    return merged[middle];
  }
  return (merged[middle - 1] + merged[middle]) / 2;
}
