export function findAllOccurrences(text: string, pattern: string): number[] {
  const found: number[] = [];
  for (let start = 0; start + pattern.length <= text.length; start++) {
    let offset = 0;
    while (offset < pattern.length && text[start + offset] === pattern[offset]) {
      offset++;
    }
    if (offset === pattern.length) {
      found.push(start);
    }
  }
  return found;
}
