const UNVISITED = 0;
const ON_PATH = 1;
const DONE = 2;

export function canFinish(numCourses: number, prerequisites: number[][]): boolean {
  const required: number[][] = Array.from({ length: numCourses }, () => []);
  for (const [course, before] of prerequisites) {
    required[course].push(before);
  }
  const state = new Array<number>(numCourses).fill(UNVISITED);
  // Whether every prerequisite chain below course ends without looping.
  const completes = (course: number): boolean => {
    state[course] = ON_PATH;
    for (const before of required[course]) {
      if (state[before] === ON_PATH) {
        return false; // the chain came back to a course still being explored
      }
      if (state[before] === UNVISITED && !completes(before)) {
        return false;
      }
    }
    state[course] = DONE;
    return true;
  };
  for (let course = 0; course < numCourses; course++) {
    if (state[course] === UNVISITED && !completes(course)) {
      return false;
    }
  }
  return true;
}
