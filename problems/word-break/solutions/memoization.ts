const UNKNOWN = 0;
const YES = 1;
const NO = 2;

export function wordBreak(s: string, wordDict: string[]): boolean {
  // memo[start] answers "can the suffix s[start..] be split into dictionary words?".
  const memo = new Uint8Array(s.length);
  const canSplitFrom = (start: number): boolean => {
    if (start === s.length) {
      return true;
    }
    if (memo[start] === UNKNOWN) {
      memo[start] = NO;
      for (const word of wordDict) {
        if (s.startsWith(word, start) && canSplitFrom(start + word.length)) {
          memo[start] = YES;
          break;
        }
      }
    }
    return memo[start] === YES;
  };
  return canSplitFrom(0);
}
