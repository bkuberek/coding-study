export function containsDuplicate(nums: number[]): boolean {
  // A typed array sorts numerically without a comparator and leaves `nums` untouched.
  const ordered = Int32Array.from(nums).sort();
  for (let i = 1; i < ordered.length; i++) {
    if (ordered[i] === ordered[i - 1]) {
      return true;
    }
  }
  return false;
}
