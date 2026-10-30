package tax_brackets

import "github.com/shopspring/decimal"

func calculateTax(brackets [][]int, income int) decimal.Decimal {
	cents := 0 // tax in hundredths of a unit: every rate is a whole percent
	bracket := 0
	for unit := 0; unit < income; unit++ {
		// Unit number unit covers income from unit to unit + 1.
		for brackets[bracket][0] <= unit {
			bracket++
		}
		cents += brackets[bracket][1]
	}
	// Built once, from the integer count of hundredths: no division, no rounding.
	return decimal.New(int64(cents), -2)
}
