export function longestPalindrome(s: string): string {
  let bestStart = 0;
  let bestLength = 1;
  // Center c sits on character c / 2 when c is even, between two characters when c is odd.
  for (let center = 0; center < 2 * s.length - 1; center++) {
    let left = center >> 1;
    let right = (center + 1) >> 1;
    while (left >= 0 && right < s.length && s[left] === s[right]) {
      left--;
      right++;
    }
    // The loop overshoots by one on each side: the palindrome is s[left + 1 .. right - 1].
    if (right - left - 1 > bestLength) {
      bestStart = left + 1;
      bestLength = right - left - 1;
    }
  }
  return s.slice(bestStart, bestStart + bestLength);
}
