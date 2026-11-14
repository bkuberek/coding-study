export function combinationSum(candidates: number[], target: number): number[][] {
  const ordered = [...candidates].sort((a, b) => a - b);
  const result: number[][] = [];
  const chosen: number[] = [];
  const extend = (start: number, remaining: number): void => {
    if (remaining === 0) {
      result.push([...chosen]);
      return;
    }
    // Values are added in non-decreasing order, so each combination is built once.
    for (let i = start; i < ordered.length && ordered[i] <= remaining; i++) {
      chosen.push(ordered[i]);
      extend(i, remaining - ordered[i]);
      chosen.pop();
    }
  };
  extend(0, target);
  return result;
}
