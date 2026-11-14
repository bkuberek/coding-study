const LEVELS = [
  ["*", "/"],
  ["+", "-"],
];

function apply(operator: string, left: number, right: number): number {
  switch (operator) {
    case "+":
      return left + right;
    case "-":
      return left - right;
    case "*":
      return left * right;
    default:
      return Math.trunc(left / right);
  }
}

export function calculate(s: string): number {
  const tokens = s.match(/\d+|[-+*/]/g) ?? [];
  const values = tokens.filter((_, i) => i % 2 === 0).map(Number);
  const operators = tokens.filter((_, i) => i % 2 === 1); // operators[i] joins values[i] and values[i + 1]
  for (const level of LEVELS) {
    for (;;) {
      // findIndex scans from the front every time: O(n) per reduction.
      const position = operators.findIndex((operator) => level.includes(operator));
      if (position === -1) {
        break;
      }
      values.splice(position, 2, apply(operators[position], values[position], values[position + 1]));
      operators.splice(position, 1);
    }
  }
  return values[0];
}
