export function isAnagram(s: string, t: string): boolean {
  if (s.length !== t.length) {
    return false;
  }
  const used = new Array<boolean>(t.length).fill(false);
  for (const letter of s) {
    let position = 0;
    while (position < t.length && (used[position] || t[position] !== letter)) {
      position++;
    }
    if (position === t.length) {
      return false;
    }
    used[position] = true;
  }
  return true;
}
