export function partitionLabels(s: string): number[] {
  const sizes: number[] = [];
  let start = 0;
  while (start < s.length) {
    // The piece must reach the last copy of every letter it contains.
    let end = s.lastIndexOf(s[start]);
    for (let position = start; position <= end; position++) {
      end = Math.max(end, s.lastIndexOf(s[position]));
    }
    sizes.push(end - start + 1);
    start = end + 1;
  }
  return sizes;
}
