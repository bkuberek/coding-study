export function permute(nums: number[]): number[][] {
  const result: number[][] = [];
  const ordering: number[] = [];
  const used = new Array<boolean>(nums.length).fill(false);
  const fillNextSlot = (): void => {
    if (ordering.length === nums.length) {
      result.push([...ordering]);
      return;
    }
    for (let i = 0; i < nums.length; i++) {
      if (used[i]) {
        continue;
      }
      used[i] = true;
      ordering.push(nums[i]);
      fillNextSlot();
      ordering.pop();
      used[i] = false;
    }
  };
  fillNextSlot();
  return result;
}
