export function rob(nums: number[]): number {
  // Before each house: withoutLast and withLast are the best totals for the prefixes that
  // end two houses back and one house back.
  let withoutLast = 0;
  let withLast = 0;
  for (const cash of nums) {
    [withoutLast, withLast] = [withLast, Math.max(withLast, withoutLast + cash)];
  }
  return withLast;
}
