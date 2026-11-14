export function findOrder(numCourses: number, prerequisites: number[][]): number[] {
  const unlocks: number[][] = Array.from({ length: numCourses }, () => []);
  const waiting = new Array<number>(numCourses).fill(0); // prerequisites each course still waits for
  for (const [course, before] of prerequisites) {
    unlocks[before].push(course);
    waiting[course]++;
  }
  // An array with a head index is the queue: shift() would cost O(n) per call.
  const ready: number[] = [];
  for (let course = 0; course < numCourses; course++) {
    if (waiting[course] === 0) {
      ready.push(course);
    }
  }
  for (let head = 0; head < ready.length; head++) {
    for (const unlocked of unlocks[ready[head]]) {
      if (--waiting[unlocked] === 0) {
        ready.push(unlocked);
      }
    }
  }
  // Courses never taken wait, directly or not, on a cycle.
  return ready.length === numCourses ? ready : [];
}
