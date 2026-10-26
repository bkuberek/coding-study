export function findMedianSortedArrays(nums1: number[], nums2: number[]): number {
  const total = nums1.length + nums2.length;
  let i = 0;
  let j = 0;
  let previous = 0;
  let current = 0;
  // Advance through the merged order until `current` is the value at position total / 2.
  for (let step = 0; step <= total >> 1; step++) {
    previous = current;
    if (j === nums2.length || (i < nums1.length && nums1[i] <= nums2[j])) {
      current = nums1[i++];
    } else {
      current = nums2[j++];
    }
  }
  return total % 2 === 1 ? current : (previous + current) / 2;
}
