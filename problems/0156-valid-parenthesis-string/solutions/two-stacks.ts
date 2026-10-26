export function checkValidString(s: string): boolean {
  const opens: number[] = []; // positions of unmatched "("
  const stars: number[] = []; // positions of unused "*"
  for (let position = 0; position < s.length; position++) {
    const char = s[position];
    if (char === "(") {
      opens.push(position);
    } else if (char === "*") {
      stars.push(position);
    } else if (opens.length > 0) {
      opens.pop(); // prefer a real "(" and keep wildcards for later
    } else if (stars.length > 0) {
      stars.pop();
    } else {
      return false;
    }
  }
  // Every remaining "(" needs a later "*" to act as its ")".
  while (opens.length > 0 && stars.length > 0) {
    if (opens.pop()! > stars.pop()!) {
      return false;
    }
  }
  return opens.length === 0;
}
