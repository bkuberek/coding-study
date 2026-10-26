const APPLY = new Map<string, (left: number, right: number) => number>([
  ["+", (left, right) => left + right],
  ["-", (left, right) => left - right],
  ["*", (left, right) => left * right],
  // Math.trunc rounds toward zero, as the statement requires.
  ["/", (left, right) => Math.trunc(left / right)],
]);

export function evalRPN(tokens: string[]): number {
  const operands: number[] = [];
  for (const token of tokens) {
    const apply = APPLY.get(token);
    if (apply === undefined) {
      operands.push(Number(token));
    } else {
      const right = operands.pop() as number;
      const left = operands.pop() as number;
      operands.push(apply(left, right));
    }
  }
  return operands[0];
}
