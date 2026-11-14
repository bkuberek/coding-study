export function subsets(nums: number[]): number[][] {
  const result: number[][] = [];
  const chosen: number[] = [];
  const explore = (index: number): void => {
    if (index === nums.length) {
      result.push([...chosen]);
      return;
    }
    chosen.push(nums[index]);
    explore(index + 1);
    chosen.pop();
    explore(index + 1);
  };
  explore(0);
  return result;
}
