import { Decimal } from "#support";

export function bondPremium(
  contractPrice: Decimal,
  bandFloors: Decimal[],
  ratesPerThousand: Decimal[],
): Decimal {
  let total = new Decimal(0); // sum of slice * rate, exact
  for (let band = 0; band < bandFloors.length; band += 1) {
    const lower = bandFloors[band];
    if (contractPrice.lte(lower)) {
      break;
    }
    const nextFloor = band + 1 < bandFloors.length ? bandFloors[band + 1] : contractPrice;
    const upper = contractPrice.lt(nextFloor) ? contractPrice : nextFloor;
    total = total.plus(upper.minus(lower).times(ratesPerThousand[band]));
  }
  // Dividing by 1000 only moves the point, so it is exact; round once, at the end.
  return total.movePointLeft(3).round(2, "HALF_UP");
}
