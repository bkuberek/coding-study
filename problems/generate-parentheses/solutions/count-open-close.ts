export function generateParenthesis(n: number): string[] {
  const result: string[] = [];
  const brackets: string[] = [];
  const extend = (opened: number, closed: number): void => {
    if (closed === n) {
      result.push(brackets.join(""));
      return;
    }
    if (opened < n) {
      brackets.push("(");
      extend(opened + 1, closed);
      brackets.pop();
    }
    // A ")" is allowed only while it has an unmatched "(" to close.
    if (closed < opened) {
      brackets.push(")");
      extend(opened, closed + 1);
      brackets.pop();
    }
  };
  extend(0, 0);
  return result;
}
