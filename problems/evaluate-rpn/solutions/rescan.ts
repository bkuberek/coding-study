type Item = number | string;

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

export function evalRPN(tokens: string[]): number {
  const isOperator = (token: string): boolean => token.length === 1 && "+-*/".includes(token);
  const items: Item[] = tokens.map((token) => (isOperator(token) ? token : Number(token)));
  while (items.length > 1) {
    // The leftmost operator always has its two operands directly in front of it.
    const position = items.findIndex((item) => typeof item === "string");
    const left = items[position - 2] as number;
    const right = items[position - 1] as number;
    items.splice(position - 2, 3, apply(items[position] as string, left, right));
  }
  return items[0] as number;
}
