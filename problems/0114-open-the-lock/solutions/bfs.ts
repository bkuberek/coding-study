const START = "0000";

// The eight settings one move away: each wheel up or down by one, wrapping around.
function turns(setting: string): string[] {
  const result: string[] = [];
  for (let wheel = 0; wheel < 4; wheel++) {
    const digit = Number(setting[wheel]);
    for (const turn of [1, 9]) {
      result.push(setting.slice(0, wheel) + String((digit + turn) % 10) + setting.slice(wheel + 1));
    }
  }
  return result;
}

export function openLock(deadends: string[], target: string): number {
  // Dead ends behave like settings that were already visited: the search never enters them.
  const seen = new Set(deadends);
  if (seen.has(START)) return -1;
  seen.add(START);
  let level = [START];
  for (let moves = 0; level.length > 0; moves++) {
    const next: string[] = [];
    for (const setting of level) {
      if (setting === target) return moves;
      for (const following of turns(setting)) {
        if (!seen.has(following)) {
          seen.add(following);
          next.push(following);
        }
      }
    }
    level = next;
  }
  return -1;
}
