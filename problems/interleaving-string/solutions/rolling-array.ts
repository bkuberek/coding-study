export function isInterleave(s1: string, s2: string, s3: string): boolean {
  if (s1.length + s2.length !== s3.length) {
    return false;
  }
  // Swapping the sources does not change the answer, so let the row run along the shorter.
  const [longer, shorter] = s1.length >= s2.length ? [s1, s2] : [s2, s1];
  // Before row i is processed, reach[j] tells whether longer[:i - 1] and shorter[:j]
  // interleave to s3[:i - 1 + j]; afterwards it holds row i.
  const reach = new Array<boolean>(shorter.length + 1).fill(false);
  for (let i = 0; i <= longer.length; i++) {
    for (let j = 0; j <= shorter.length; j++) {
      if (i === 0 && j === 0) {
        reach[j] = true;
        continue;
      }
      const fromLonger = i > 0 && reach[j] && longer[i - 1] === s3[i + j - 1];
      const fromShorter = j > 0 && reach[j - 1] && shorter[j - 1] === s3[i + j - 1];
      reach[j] = fromLonger || fromShorter;
    }
  }
  return reach[shorter.length];
}
