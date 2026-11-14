function isDigit(character: string): boolean {
  return character >= "0" && character <= "9";
}

export function decodeString(s: string): string {
  while (s.includes("[")) {
    // The first "]" closes an innermost group: the last "[" before it is its opener.
    const close = s.indexOf("]");
    const open = s.lastIndexOf("[", close);
    let start = open;
    while (start > 0 && isDigit(s[start - 1])) {
      start--;
    }
    const count = Number(s.slice(start, open));
    s = s.slice(0, start) + s.slice(open + 1, close).repeat(count) + s.slice(close + 1);
  }
  return s;
}
