const PAIRS = ["()", "[]", "{}"];

export function isValid(s: string): boolean {
  for (;;) {
    let shorter = s;
    for (const pair of PAIRS) {
      shorter = shorter.replaceAll(pair, "");
    }
    if (shorter.length === s.length) {
      // Nothing left to delete: balanced exactly when nothing is left at all.
      return s.length === 0;
    }
    s = shorter;
  }
}
