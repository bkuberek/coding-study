function pairsWithNext(s: string, start: number): boolean {
  if (start + 1 >= s.length) {
    return false;
  }
  const value = Number(s.slice(start, start + 2));
  return value >= 10 && value <= 26;
}

export function numDecodings(s: string): number {
  // memo[start] is the number of readings of the suffix s[start..], or -1 when unknown.
  const memo = new Array<number>(s.length).fill(-1);
  const waysFrom = (start: number): number => {
    if (start === s.length) {
      return 1;
    }
    if (s[start] === "0") {
      return 0;
    }
    if (memo[start] === -1) {
      let count = waysFrom(start + 1);
      if (pairsWithNext(s, start)) {
        count += waysFrom(start + 2);
      }
      memo[start] = count;
    }
    return memo[start];
  };
  return waysFrom(0);
}
