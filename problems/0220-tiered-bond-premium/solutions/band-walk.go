package tiered_bond_premium

import "github.com/shopspring/decimal"

const cents = 2

func bondPremium(contractPrice decimal.Decimal, bandFloors []decimal.Decimal, ratesPerThousand []decimal.Decimal) decimal.Decimal {
	total := decimal.Zero // sum of slice * rate, exact
	for band, lower := range bandFloors {
		if contractPrice.LessThanOrEqual(lower) {
			break
		}
		upper := contractPrice
		if band+1 < len(bandFloors) {
			upper = bandFloors[band+1]
		}
		slice := decimal.Min(contractPrice, upper).Sub(lower)
		total = total.Add(slice.Mul(ratesPerThousand[band]))
	}
	// Shift only moves the point, so dividing by 1000 is exact; round once, at the end. Round
	// breaks ties away from zero, Java's HALF_UP.
	return total.Shift(-3).Round(cents)
}
