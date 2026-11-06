// Debug: Invoice Total Cents. Some tests fail: find the bug and fix it.

const BASIS_POINTS = 10000;

export function invoiceTotalCents(
  unitPrices: string[],
  quantities: number[],
  taxBasisPoints: number,
): number {
  let subtotal = 0;
  unitPrices.forEach((price, line) => {
    subtotal += Number(price) * quantities[line];
  });
  const tax = subtotal * (taxBasisPoints / BASIS_POINTS);
  return Math.trunc((subtotal + tax) * 100);
}
