export function findAllOccurrences(text: string, pattern: string): number[] {
  const border = borderTable(pattern);
  const found: number[] = [];
  let matched = 0;
  for (let position = 0; position < text.length; position++) {
    while (matched > 0 && text[position] !== pattern[matched]) {
      matched = border[matched - 1];
    }
    if (text[position] === pattern[matched]) {
      matched++;
    }
    if (matched === pattern.length) {
      found.push(position - pattern.length + 1);
      matched = border[matched - 1];
    }
  }
  return found;
}

// border[i] is the length of the longest proper prefix of pattern[0..i] that is also a suffix of it.
function borderTable(pattern: string): number[] {
  const border: number[] = new Array(pattern.length).fill(0);
  let length = 0;
  for (let i = 1; i < pattern.length; i++) {
    while (length > 0 && pattern[i] !== pattern[length]) {
      length = border[length - 1];
    }
    if (pattern[i] === pattern[length]) {
      length++;
    }
    border[i] = length;
  }
  return border;
}
