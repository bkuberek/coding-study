export function combinationSum(candidates: number[], target: number): number[][] {
  const result: number[][] = [];
  const chosen: number[] = [];
  const explore = (index: number, remaining: number): void => {
    if (remaining === 0) {
      result.push([...chosen]);
      return;
    }
    if (remaining < 0 || index === candidates.length) {
      return;
    }
    // Use candidates[index] once more and stay on it, since it may repeat.
    chosen.push(candidates[index]);
    explore(index, remaining - candidates[index]);
    chosen.pop();
    // Or never use it again.
    explore(index + 1, remaining);
  };
  explore(0, target);
  return result;
}
