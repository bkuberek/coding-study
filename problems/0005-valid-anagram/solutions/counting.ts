const ALPHABET_SIZE = 26;
const BASE = "a".charCodeAt(0);

export function isAnagram(s: string, t: string): boolean {
  if (s.length !== t.length) {
    return false;
  }
  const counts = new Int32Array(ALPHABET_SIZE);
  for (let i = 0; i < s.length; i++) {
    counts[s.charCodeAt(i) - BASE]++;
  }
  for (let i = 0; i < t.length; i++) {
    const index = t.charCodeAt(i) - BASE;
    counts[index]--;
    if (counts[index] < 0) {
      return false;
    }
  }
  return true;
}
