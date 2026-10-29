export function numOfMinutes(
  n: number,
  headID: number,
  manager: number[],
  informTime: number[],
): number {
  const reports: number[][] = Array.from({ length: n }, () => []);
  manager.forEach((boss, employee) => {
    if (boss !== -1) {
      reports[boss].push(employee);
    }
  });
  let longest = 0;
  // Each entry is [employee, minute at which they hear the news].
  const pending: [number, number][] = [[headID, 0]];
  while (pending.length > 0) {
    const [employee, heardAt] = pending.pop() as [number, number];
    longest = Math.max(longest, heardAt);
    const passedOnAt = heardAt + informTime[employee];
    for (const report of reports[employee]) {
      pending.push([report, passedOnAt]);
    }
  }
  return longest;
}
