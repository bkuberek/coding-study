export function partition(s: string): string[][] {
  const result: string[][] = [];
  const pieces: string[] = [];
  const isPalindrome = (left: number, right: number): boolean => {
    for (; left < right; left++, right--) {
      if (s[left] !== s[right]) {
        return false;
      }
    }
    return true;
  };
  const cutFrom = (start: number): void => {
    if (start === s.length) {
      result.push([...pieces]);
      return;
    }
    for (let end = start; end < s.length; end++) {
      if (isPalindrome(start, end)) {
        pieces.push(s.slice(start, end + 1));
        cutFrom(end + 1);
        pieces.pop();
      }
    }
  };
  cutFrom(0);
  return result;
}
