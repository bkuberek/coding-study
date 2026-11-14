const BASE = 131;
const MODULUS = 1_000_000_007;

export function findAllOccurrences(text: string, pattern: string): number[] {
  const windowSize = pattern.length;
  if (windowSize > text.length) {
    return [];
  }
  // Every product below stays under 2^53: a residue is below 1e9 + 7 and the factor is at most 131.
  let leavingWeight = 1;
  for (let i = 1; i < windowSize; i++) {
    leavingWeight = (leavingWeight * BASE) % MODULUS;
  }
  let target = 0;
  let window = 0;
  for (let i = 0; i < windowSize; i++) {
    target = (target * BASE + pattern.charCodeAt(i)) % MODULUS;
    window = (window * BASE + text.charCodeAt(i)) % MODULUS;
  }
  const found: number[] = [];
  for (let start = 0; start + windowSize <= text.length; start++) {
    if (window === target && text.startsWith(pattern, start)) {
      found.push(start);
    }
    if (start + windowSize < text.length) {
      const without = (window - ((text.charCodeAt(start) * leavingWeight) % MODULUS) + MODULUS) % MODULUS;
      window = (without * BASE + text.charCodeAt(start + windowSize)) % MODULUS;
    }
  }
  return found;
}
