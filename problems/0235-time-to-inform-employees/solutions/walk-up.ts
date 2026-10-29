export function numOfMinutes(
  n: number,
  headID: number,
  manager: number[],
  informTime: number[],
): number {
  let longest = 0;
  for (let employee = 0; employee < n; employee++) {
    // The news reaches employee after every manager above them has passed it on.
    let elapsed = 0;
    let current = employee;
    while (current !== headID) {
      current = manager[current];
      elapsed += informTime[current];
    }
    longest = Math.max(longest, elapsed);
  }
  return longest;
}
