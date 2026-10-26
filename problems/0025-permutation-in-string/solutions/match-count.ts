export function checkInclusion(pattern: string, text: string): boolean {
  const width = pattern.length;
  if (width > text.length) {
    return false;
  }
  const surplus = new Int32Array(26);
  for (let i = 0; i < width; i++) {
    surplus[pattern.charCodeAt(i) - 97]--;
  }
  let balanced = surplus.filter((value) => value === 0).length;
  const shift = (letter: number, delta: number): void => {
    if (surplus[letter] === 0) {
      balanced--;
    }
    surplus[letter] += delta;
    if (surplus[letter] === 0) {
      balanced++;
    }
  };
  for (let right = 0; right < text.length; right++) {
    shift(text.charCodeAt(right) - 97, 1);
    if (right >= width) {
      shift(text.charCodeAt(right - width) - 97, -1);
    }
    if (balanced === 26) {
      return true;
    }
  }
  return false;
}
