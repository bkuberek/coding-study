export function minMeetingRooms(intervals: number[][]): number {
  // The busiest moment is always the start of some meeting.
  let rooms = 0;
  for (const [moment] of intervals) {
    let running = 0;
    for (const [start, end] of intervals) {
      if (start <= moment && moment < end) {
        running++;
      }
    }
    rooms = Math.max(rooms, running);
  }
  return rooms;
}
