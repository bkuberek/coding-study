package tax_brackets

import "github.com/shopspring/decimal"

func calculateTax(brackets [][]int, income int) decimal.Decimal {
	cents := 0 // tax in hundredths of a unit: every rate is a whole percent
	lower := 0
	for _, bracket := range brackets {
		if lower >= income {
			break
		}
		cents += (min(bracket[0], income) - lower) * bracket[1]
		lower = bracket[0]
	}
	// Built once, from the integer count of hundredths: no division, no rounding.
	return decimal.New(int64(cents), -2)
}
