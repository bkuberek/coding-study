package premium_rating_breakdown

import (
	"sort"

	"github.com/shopspring/decimal"
)

const cents = 2

func ratePremium(classCode string, payroll decimal.Decimal, experienceMod decimal.Decimal, scheduleCredit decimal.Decimal, classCodes []string, baseRates []decimal.Decimal, bandLowerBounds []decimal.Decimal, bandFactors []decimal.Decimal, minimumPremium decimal.Decimal) []decimal.Decimal {
	rates := make(map[string]decimal.Decimal, len(classCodes))
	for i, code := range classCodes {
		rates[code] = baseRates[i]
	}
	// Bands whose lower bound is <= payroll (upper bound of the sorted bounds).
	band := sort.Search(len(bandLowerBounds), func(i int) bool {
		return bandLowerBounds[i].GreaterThan(payroll)
	}) - 1
	rate, known := rates[classCode]
	if !known || band < 0 {
		return []decimal.Decimal{}
	}
	// Shift only moves the decimal point, so dividing by 1000 stays exact.
	running := payroll.Shift(-3).Mul(rate)
	trail := []decimal.Decimal{running}
	for _, factor := range []decimal.Decimal{bandFactors[band], experienceMod, decimal.NewFromInt(1).Sub(scheduleCredit)} {
		running = running.Mul(factor)
		trail = append(trail, running)
	}
	// Round: ties away from zero, Java's HALF_UP.
	return append(trail, decimal.Max(running, minimumPremium).Round(cents))
}
