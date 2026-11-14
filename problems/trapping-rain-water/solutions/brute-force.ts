export function trap(height: number[]): number {
  let water = 0;
  for (let i = 0; i < height.length; i++) {
    let leftMax = 0;
    for (let j = 0; j <= i; j++) {
      leftMax = Math.max(leftMax, height[j]);
    }
    let rightMax = 0;
    for (let j = i; j < height.length; j++) {
      rightMax = Math.max(rightMax, height[j]);
    }
    water += Math.min(leftMax, rightMax) - height[i];
  }
  return water;
}
