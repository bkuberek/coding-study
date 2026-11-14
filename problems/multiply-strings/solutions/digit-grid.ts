const ZERO = "0".charCodeAt(0);

export function multiply(num1: string, num2: string): string {
  if (num1 === "0" || num2 === "0") {
    return "0";
  }
  const m = num1.length;
  const n = num2.length;
  // digits[k] is result digit k counted from the left; the product has at most m + n digits.
  const digits = new Uint8Array(m + n);
  for (let i = m - 1; i >= 0; i--) {
    const a = num1.charCodeAt(i) - ZERO;
    let carry = 0;
    for (let j = n - 1; j >= 0; j--) {
      const value = digits[i + j + 1] + a * (num2.charCodeAt(j) - ZERO) + carry;
      digits[i + j + 1] = value % 10;
      carry = Math.floor(value / 10);
    }
    digits[i] += carry;
  }
  const start = digits[0] === 0 ? 1 : 0; // at most one leading zero
  let text = "";
  for (let k = start; k < digits.length; k++) {
    text += String.fromCharCode(ZERO + digits[k]);
  }
  return text;
}
