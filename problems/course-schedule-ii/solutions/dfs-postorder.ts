const UNSEEN = 0;
const ACTIVE = 1;
const DONE = 2;

export function findOrder(numCourses: number, prerequisites: number[][]): number[] {
  const required: number[][] = Array.from({ length: numCourses }, () => []);
  for (const [course, before] of prerequisites) {
    required[course].push(before);
  }
  const state = new Array<number>(numCourses).fill(UNSEEN);
  const cursor = new Array<number>(numCourses).fill(0); // next prerequisite to visit, per course
  const order: number[] = [];
  for (let root = 0; root < numCourses; root++) {
    if (state[root] !== UNSEEN) {
      continue;
    }
    state[root] = ACTIVE;
    const stack = [root];
    while (stack.length > 0) {
      const course = stack[stack.length - 1];
      if (cursor[course] === required[course].length) {
        // Every prerequisite is already in the order: the course can follow them.
        stack.pop();
        state[course] = DONE;
        order.push(course);
        continue;
      }
      const before = required[course][cursor[course]++];
      if (state[before] === ACTIVE) {
        return []; // the path loops back to a course still being explored
      }
      if (state[before] === UNSEEN) {
        state[before] = ACTIVE;
        stack.push(before);
      }
    }
  }
  return order;
}
