function isBalanced(brackets: string[]): boolean {
  // depth is the height a stack of unmatched "(" would have.
  let depth = 0;
  for (const bracket of brackets) {
    depth += bracket === "(" ? 1 : -1;
    if (depth < 0) {
      return false;
    }
  }
  return depth === 0;
}

export function generateParenthesis(n: number): string[] {
  const result: string[] = [];
  const brackets = new Array<string>(2 * n);
  // Writes every arrangement of the remaining brackets, without looking at their order.
  const arrange = (position: number, openingLeft: number, closingLeft: number): void => {
    if (position === 2 * n) {
      if (isBalanced(brackets)) {
        result.push(brackets.join(""));
      }
      return;
    }
    if (openingLeft > 0) {
      brackets[position] = "(";
      arrange(position + 1, openingLeft - 1, closingLeft);
    }
    if (closingLeft > 0) {
      brackets[position] = ")";
      arrange(position + 1, openingLeft, closingLeft - 1);
    }
  };
  arrange(0, n, n);
  return result;
}
