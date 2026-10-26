export function dailyTemperatures(temperatures: number[]): number[] {
  const days = temperatures.length;
  const waits = new Array<number>(days).fill(0);
  for (let day = 0; day < days; day++) {
    for (let later = day + 1; later < days; later++) {
      if (temperatures[later] > temperatures[day]) {
        waits[day] = later - day;
        break;
      }
    }
  }
  return waits;
}
