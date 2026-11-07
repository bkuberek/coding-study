// The derived numbers, in integer cents, with no floating point on the way. The stated rounding rule
// (half up) holds exactly because the whole calculation is one fraction, divided once.

const BPS_PER_MONTH_UNIT = 120_000n;

/** n / d, to the nearest whole number, a half going up. */
function divideHalfUp(numerator: bigint, denominator: bigint): bigint {
  return (2n * numerator + denominator) / (2n * denominator);
}

/**
 * The fixed monthly payment: `P r / (1 - (1 + r)^-n)`, with `r = rateBps / 120000` a month. Written
 * over a common denominator, it is `P b (U + b)^n / (U ((U + b)^n - U^n))`, with `U = 120000`.
 */
export function monthlyPaymentCents(amountCents: number, rateBps: number, termMonths: number): number {
  const amount = BigInt(amountCents);
  const months = BigInt(termMonths);
  if (rateBps === 0) {
    return Number(divideHalfUp(amount, months));
  }
  const rate = BigInt(rateBps);
  const grown = (BPS_PER_MONTH_UNIT + rate) ** months;
  const flat = BPS_PER_MONTH_UNIT ** months;
  return Number(divideHalfUp(amount * rate * grown, BPS_PER_MONTH_UNIT * (grown - flat)));
}

export interface Derived {
  monthlyPaymentCents: number;
  totalRepaidCents: number;
  financeChargeCents: number;
  paymentToIncomeBps: number;
  statedPaymentMatches: boolean;
}

export function derive(
  amountCents: number,
  rateBps: number,
  termMonths: number,
  monthlyIncomeCents: number,
  statedPaymentCents: number,
): Derived {
  const payment = monthlyPaymentCents(amountCents, rateBps, termMonths);
  const total = payment * termMonths;
  return {
    monthlyPaymentCents: payment,
    totalRepaidCents: total,
    financeChargeCents: total - amountCents,
    paymentToIncomeBps: Number(divideHalfUp(BigInt(payment) * 10_000n, BigInt(monthlyIncomeCents))),
    statedPaymentMatches: payment === statedPaymentCents,
  };
}
