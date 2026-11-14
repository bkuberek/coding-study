export function canAttendMeetings(intervals: number[][]): boolean {
  for (let i = 0; i < intervals.length; i++) {
    const [firstStart, firstEnd] = intervals[i];
    for (let j = i + 1; j < intervals.length; j++) {
      const [secondStart, secondEnd] = intervals[j];
      // Half-open meetings share a moment exactly when each starts before the other ends.
      if (firstStart < secondEnd && secondStart < firstEnd) {
        return false;
      }
    }
  }
  return true;
}
