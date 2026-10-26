export function removeKDigits(num: string, k: number): string {
  // The digits kept so far; they never decrease from bottom to top.
  const kept: string[] = [];
  let remaining = k;
  for (const digit of num) {
    while (remaining > 0 && kept.length > 0 && kept[kept.length - 1] > digit) {
      kept.pop();
      remaining--;
    }
    kept.push(digit);
  }
  // The kept digits never decrease, so leftover deletions are cheapest at the end.
  kept.length -= remaining;
  let start = 0;
  while (start < kept.length && kept[start] === "0") {
    start++;
  }
  return start === kept.length ? "0" : kept.slice(start).join("");
}
