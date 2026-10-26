export function partition(s: string): string[][] {
  const n = s.length;
  // palindrome[i][j]: whether s[i..j] reads the same both ways. Row i depends on row i + 1.
  const palindrome = Array.from({ length: n }, () => new Array<boolean>(n).fill(false));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = i; j < n; j++) {
      palindrome[i][j] = s[i] === s[j] && (j - i < 2 || palindrome[i + 1][j - 1]);
    }
  }
  const result: string[][] = [];
  const pieces: string[] = [];
  const cutFrom = (start: number): void => {
    if (start === n) {
      result.push([...pieces]);
      return;
    }
    for (let end = start; end < n; end++) {
      if (palindrome[start][end]) {
        pieces.push(s.slice(start, end + 1));
        cutFrom(end + 1);
        pieces.pop();
      }
    }
  };
  cutFrom(0);
  return result;
}
