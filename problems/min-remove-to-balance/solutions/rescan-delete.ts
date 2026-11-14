// A parenthesis that cannot be matched, or -1 when `s` is balanced.
function firstOffender(s: string): number {
  let depth = 0;
  for (let position = 0; position < s.length; position++) {
    if (s[position] === "(") {
      depth++;
    } else if (s[position] === ")") {
      if (depth === 0) {
        return position; // a closer with nothing open before it
      }
      depth--;
    }
  }
  if (depth === 0) {
    return -1;
  }
  // Some openers are never closed: the last opener with no closer left after it is one.
  let closers = 0;
  for (let position = s.length - 1; position >= 0; position--) {
    if (s[position] === ")") {
      closers++;
    } else if (s[position] === "(") {
      if (closers === 0) {
        return position;
      }
      closers--;
    }
  }
  return -1;
}

export function minRemoveToMakeValid(s: string): string {
  for (let position = firstOffender(s); position !== -1; position = firstOffender(s)) {
    s = s.slice(0, position) + s.slice(position + 1);
  }
  return s;
}
