export function leastInterval(tasks: string[], cooldown: number): number {
  const counts = new Array<number>(26).fill(0);
  for (const task of tasks) {
    counts[task.charCodeAt(0) - 65]++;
  }
  const top = Math.max(...counts);
  const tied = counts.filter((count) => count === top).length;
  // top - 1 full frames of cooldown + 1 slots, then one last partial frame holding the
  // tied most frequent tasks. With enough other tasks, no slot idles.
  return Math.max(tasks.length, (top - 1) * (cooldown + 1) + tied);
}
