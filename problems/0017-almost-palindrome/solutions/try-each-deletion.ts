function isPalindrome(text: string): boolean {
  for (let left = 0, right = text.length - 1; left < right; left++, right--) {
    if (text.charCodeAt(left) !== text.charCodeAt(right)) {
      return false;
    }
  }
  return true;
}

export function validPalindrome(s: string): boolean {
  if (isPalindrome(s)) {
    return true;
  }
  for (let index = 0; index < s.length; index++) {
    if (isPalindrome(s.slice(0, index) + s.slice(index + 1))) {
      return true;
    }
  }
  return false;
}
