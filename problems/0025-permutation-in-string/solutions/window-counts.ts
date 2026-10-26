function sameCounts(a: Int32Array, b: Int32Array): boolean {
  for (let i = 0; i < 26; i++) {
    if (a[i] !== b[i]) {
      return false;
    }
  }
  return true;
}

export function checkInclusion(pattern: string, text: string): boolean {
  const width = pattern.length;
  if (width > text.length) {
    return false;
  }
  const need = new Int32Array(26);
  const window = new Int32Array(26);
  for (let i = 0; i < width; i++) {
    need[pattern.charCodeAt(i) - 97]++;
  }
  for (let right = 0; right < text.length; right++) {
    window[text.charCodeAt(right) - 97]++;
    if (right >= width) {
      window[text.charCodeAt(right - width) - 97]--;
    }
    if (right >= width - 1 && sameCounts(window, need)) {
      return true;
    }
  }
  return false;
}
