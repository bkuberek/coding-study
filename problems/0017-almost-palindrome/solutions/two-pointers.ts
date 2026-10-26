function isPalindromeRange(s: string, left: number, right: number): boolean {
  while (left < right) {
    if (s.charCodeAt(left) !== s.charCodeAt(right)) {
      return false;
    }
    left++;
    right--;
  }
  return true;
}

export function validPalindrome(s: string): boolean {
  let left = 0;
  let right = s.length - 1;
  while (left < right) {
    if (s.charCodeAt(left) !== s.charCodeAt(right)) {
      return isPalindromeRange(s, left + 1, right) || isPalindromeRange(s, left, right - 1);
    }
    left++;
    right--;
  }
  return true;
}
