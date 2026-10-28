import { Decimal } from "#support";

// Number of bands whose lower bound is <= payroll (upper bound of the sorted bounds).
function bandsAtOrBelow(bounds: Decimal[], payroll: Decimal): number {
  let low = 0;
  let high = bounds.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (bounds[middle].cmp(payroll) <= 0) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }
  return low;
}

export function ratePremium(
  classCode: string,
  payroll: Decimal,
  experienceMod: Decimal,
  scheduleCredit: Decimal,
  classCodes: string[],
  baseRates: Decimal[],
  bandLowerBounds: Decimal[],
  bandFactors: Decimal[],
  minimumPremium: Decimal,
): Decimal[] {
  const rates = new Map<string, Decimal>();
  classCodes.forEach((code, i) => rates.set(code, baseRates[i]));
  const band = bandsAtOrBelow(bandLowerBounds, payroll) - 1;
  const rate = rates.get(classCode);
  if (rate === undefined || band < 0) {
    return [];
  }
  // Dividing by 1000 only moves the decimal point, so it stays exact.
  let running = payroll.movePointLeft(3).times(rate);
  const trail = [running];
  const factors = [bandFactors[band], experienceMod, new Decimal(1).minus(scheduleCredit)];
  for (const factor of factors) {
    running = running.times(factor);
    trail.push(running);
  }
  const floored = running.lt(minimumPremium) ? minimumPremium : running;
  trail.push(floored.round(2, "HALF_UP"));
  return trail;
}
