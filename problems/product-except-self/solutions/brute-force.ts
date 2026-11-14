export function productExceptSelf(nums: number[]): number[] {
  const answer = new Array<number>(nums.length);
  for (let i = 0; i < nums.length; i++) {
    let product = 1;
    for (let j = 0; j < nums.length; j++) {
      if (j !== i) {
        product *= nums[j];
      }
    }
    answer[i] = product;
  }
  return answer;
}
