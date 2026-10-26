function isAlphanumeric(code: number): boolean {
  return (code >= 48 && code <= 57) || (code >= 65 && code <= 90) || (code >= 97 && code <= 122);
}

function toLower(code: number): number {
  return code >= 65 && code <= 90 ? code + 32 : code;
}

export function isPalindrome(s: string): boolean {
  let left = 0;
  let right = s.length - 1;
  while (left < right) {
    const leftCode = s.charCodeAt(left);
    const rightCode = s.charCodeAt(right);
    if (!isAlphanumeric(leftCode)) {
      left++;
    } else if (!isAlphanumeric(rightCode)) {
      right--;
    } else if (toLower(leftCode) !== toLower(rightCode)) {
      return false;
    } else {
      left++;
      right--;
    }
  }
  return true;
}
