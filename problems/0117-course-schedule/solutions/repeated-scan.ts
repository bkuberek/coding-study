export function canFinish(numCourses: number, prerequisites: number[][]): boolean {
  const required: number[][] = Array.from({ length: numCourses }, () => []);
  for (const [course, before] of prerequisites) {
    required[course].push(before);
  }
  const taken = new Array<boolean>(numCourses).fill(false);
  for (let round = 0; round < numCourses; round++) {
    // Take the first course whose prerequisites are all done; give up if there is none.
    let next = -1;
    for (let course = 0; course < numCourses && next < 0; course++) {
      if (!taken[course] && required[course].every((before) => taken[before])) {
        next = course;
      }
    }
    if (next < 0) {
      return false;
    }
    taken[next] = true;
  }
  return true;
}
