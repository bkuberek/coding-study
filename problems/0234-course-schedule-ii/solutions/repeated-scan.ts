export function findOrder(numCourses: number, prerequisites: number[][]): number[] {
  const required: number[][] = Array.from({ length: numCourses }, () => []);
  for (const [course, before] of prerequisites) {
    required[course].push(before);
  }
  const taken = new Array<boolean>(numCourses).fill(false);
  const order: number[] = [];
  for (let round = 0; round < numCourses; round++) {
    // Take the first course whose prerequisites are all done; give up if there is none.
    const next = taken.findIndex(
      (done, course) => !done && required[course].every((before) => taken[before]),
    );
    if (next < 0) {
      return [];
    }
    taken[next] = true;
    order.push(next);
  }
  return order;
}
