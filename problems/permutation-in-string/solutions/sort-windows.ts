function sortedCodes(text: string, start: number, width: number): Uint8Array {
  const codes = new Uint8Array(width);
  for (let i = 0; i < width; i++) {
    codes[i] = text.charCodeAt(start + i);
  }
  return codes.sort();
}

export function checkInclusion(pattern: string, text: string): boolean {
  const width = pattern.length;
  const target = sortedCodes(pattern, 0, width);
  for (let start = 0; start + width <= text.length; start++) {
    const window = sortedCodes(text, start, width);
    if (window.every((code, i) => code === target[i])) {
      return true;
    }
  }
  return false;
}
