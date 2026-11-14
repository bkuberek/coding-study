export function isAnagram(s: string, t: string): boolean {
  if (s.length !== t.length) {
    return false;
  }
  // Default sort compares UTF-16 code units, which orders lowercase letters correctly.
  const canonical = (text: string): string => [...text].sort().join("");
  return canonical(s) === canonical(t);
}
