export function partitionLabels(s: string): number[] {
  // Each letter occupies the span from its first to its last copy. A Map keeps insertion
  // order, so its letters come by first occurrence, which sorts the spans by start.
  const spans = new Map<string, [number, number]>();
  for (let index = 0; index < s.length; index++) {
    const span = spans.get(s[index]);
    if (span === undefined) {
      spans.set(s[index], [index, index]);
    } else {
      span[1] = index;
    }
  }
  const sizes: number[] = [];
  let pieceStart = 0;
  let pieceEnd = -1;
  for (const [first, last] of spans.values()) {
    if (first > pieceEnd) {
      if (pieceEnd >= 0) {
        sizes.push(pieceEnd - pieceStart + 1);
      }
      pieceStart = first;
    }
    pieceEnd = Math.max(pieceEnd, last);
  }
  sizes.push(pieceEnd - pieceStart + 1);
  return sizes;
}
