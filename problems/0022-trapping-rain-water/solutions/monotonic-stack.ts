export function trap(height: number[]): number {
  let water = 0;
  const falling: number[] = [];
  for (let right = 0; right < height.length; right++) {
    while (falling.length > 0 && height[falling[falling.length - 1]] < height[right]) {
      const bottom = height[falling.pop()!];
      if (falling.length === 0) {
        break;
      }
      const left = falling[falling.length - 1];
      const level = Math.min(height[left], height[right]);
      water += (right - left - 1) * (level - bottom);
    }
    falling.push(right);
  }
  return water;
}
