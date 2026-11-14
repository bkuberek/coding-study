export function dailyTemperatures(temperatures: number[]): number[] {
  const waits = new Array<number>(temperatures.length).fill(0);
  // Days still waiting for a warmer day; their readings never rise from bottom to top.
  const waiting: number[] = [];
  for (let day = 0; day < temperatures.length; day++) {
    while (waiting.length > 0 && temperatures[waiting[waiting.length - 1]] < temperatures[day]) {
      const earlier = waiting.pop()!;
      waits[earlier] = day - earlier;
    }
    waiting.push(day);
  }
  return waits;
}
