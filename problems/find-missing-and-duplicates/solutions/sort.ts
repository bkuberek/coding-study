export function findMissingAndDuplicates(nums: number[]): number[][] {
  // The comparator is required: the default sort compares the values as text.
  nums.sort((a, b) => a - b);
  const missing: number[] = [];
  const duplicated: number[] = [];
  let expected = 1; // the smallest value not accounted for yet
  let previous = 0;
  for (const value of nums) {
    if (value === previous) {
      // A third copy must not list the value again.
      if (duplicated.length === 0 || duplicated[duplicated.length - 1] !== value) {
        duplicated.push(value);
      }
      continue;
    }
    for (; expected < value; expected++) {
      missing.push(expected);
    }
    expected = value + 1;
    previous = value;
  }
  for (; expected <= nums.length; expected++) {
    missing.push(expected);
  }
  return [missing, duplicated];
}
