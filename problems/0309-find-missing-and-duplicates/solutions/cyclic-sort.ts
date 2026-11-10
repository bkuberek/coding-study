export function findMissingAndDuplicates(nums: number[]): number[][] {
  const n = nums.length;
  for (let i = 0; i < n; i++) {
    // Swap nums[i] to its home index nums[i] - 1 until the home already holds that value.
    // Comparing with the home, not with i, is what stops the loop on a repeated value.
    while (nums[nums[i] - 1] !== nums[i]) {
      const home = nums[i] - 1;
      [nums[i], nums[home]] = [nums[home], nums[i]];
    }
  }

  // Every value that occurs now sits at its home. A slot that holds another value is either
  // the home of a missing value or a spare copy of a value that is home elsewhere. A negative
  // sign on a home marks that its value has a spare copy.
  const missing: number[] = [];
  for (let i = 0; i < n; i++) {
    if (Math.abs(nums[i]) === i + 1) {
      continue;
    }
    missing.push(i + 1);
    const spare = nums[i];
    nums[spare - 1] = -spare;
  }

  // The marks are read in index order, so the duplicates come out sorted too.
  const duplicated: number[] = [];
  for (let value = 1; value <= n; value++) {
    if (nums[value - 1] < 0) {
      duplicated.push(value);
    }
  }
  return [missing, duplicated];
}
