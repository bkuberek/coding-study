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
  const blocked = new Set(deadends);
  if (blocked.has(START)) return -1;
  if (target === START) return 0;
  // Two frontiers grow toward each other; moves counts the levels expanded so far.
  let near = new Set([START]);
  let far = new Set([target]);
  const seen = new Set([START, target]);
  let moves = 0;
  while (near.size > 0 && far.size > 0) {
    if (near.size > far.size) [near, far] = [far, near]; // always expand the smaller frontier
    moves++;
    const next = new Set<string>();
    for (const setting of near) {
      for (const following of turns(setting)) {
        if (far.has(following)) return moves;
        if (!seen.has(following) && !blocked.has(following)) {
          seen.add(following);
          next.add(following);
        }
      }
    }
    near = next;
  }
  return -1;
}
