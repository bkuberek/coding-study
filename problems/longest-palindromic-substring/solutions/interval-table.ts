export function longestPalindrome(s: string): string {
  const n = s.length;
  // isPalindrome[i][j] tells whether s[i..j] (inclusive) is a palindrome.
  const isPalindrome = Array.from({ length: n }, () => new Array<boolean>(n).fill(false));
  let bestStart = 0;
  let bestLength = 1;
  for (let i = 0; i < n; i++) {
    isPalindrome[i][i] = true;
  }
  for (let length = 2; length <= n; length++) {
    for (let i = 0; i + length <= n; i++) {
      const j = i + length - 1;
      if (s[i] === s[j] && (length === 2 || isPalindrome[i + 1][j - 1])) {
        isPalindrome[i][j] = true;
        bestStart = i;
        bestLength = length;
      }
    }
  }
  return s.slice(bestStart, bestStart + bestLength);
}
