const ZERO = "0".charCodeAt(0);

/** Little-endian digits of (digits * factor). */
function timesDigit(digits: number[], factor: number): number[] {
  const product: number[] = [];
  let carry = 0;
  for (const digit of digits) {
    const value = digit * factor + carry;
    product.push(value % 10);
    carry = Math.floor(value / 10);
  }
  if (carry > 0) {
    product.push(carry);
  }
  return product;
}

/** Little-endian digits of left + right. */
function add(left: number[], right: number[]): number[] {
  const total: number[] = [];
  let carry = 0;
  for (let position = 0; position < Math.max(left.length, right.length); position++) {
    const value = (left[position] ?? 0) + (right[position] ?? 0) + carry;
    total.push(value % 10);
    carry = Math.floor(value / 10);
  }
  if (carry > 0) {
    total.push(carry);
  }
  return total;
}

export function multiply(num1: string, num2: string): string {
  if (num1 === "0" || num2 === "0") {
    return "0";
  }
  const first = Array.from(num1, (ch) => ch.charCodeAt(0) - ZERO).reverse();
  let total: number[] = [];
  // School method: one row per digit of num2, shifted by its position.
  for (let shift = 0; shift < num2.length; shift++) {
    const digit = num2.charCodeAt(num2.length - 1 - shift) - ZERO;
    const row = new Array<number>(shift).fill(0).concat(timesDigit(first, digit));
    total = add(total, row);
  }
  return total.reverse().join("");
}
