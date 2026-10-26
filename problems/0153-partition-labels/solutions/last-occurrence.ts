const A = "a".charCodeAt(0);

export function partitionLabels(s: string): number[] {
  const last = new Array<number>(26).fill(-1);
  for (let index = 0; index < s.length; index++) {
    last[s.charCodeAt(index) - A] = index;
  }
  const sizes: number[] = [];
  let start = 0;
  let end = 0;
  for (let index = 0; index < s.length; index++) {
    end = Math.max(end, last[s.charCodeAt(index) - A]);
    if (index === end) {
      // Every letter seen since `start` has no copy after this point: cut here.
      sizes.push(end - start + 1);
      start = index + 1;
    }
  }
  return sizes;
}
