package loss_ratio_by_period

import (
	"time"

	"github.com/shopspring/decimal"
)

const ratioPlaces = 4

var noEarnedPremium = decimal.NewFromInt(-1)

func lossRatios(earnedDates []time.Time, earnedAmounts []decimal.Decimal, lossDates []time.Time, lossAmounts []decimal.Decimal, fromDate time.Time, toDate time.Time, periodMonths int) []decimal.Decimal {
	first := periodIndex(fromDate, periodMonths)
	count := periodIndex(toDate, periodMonths) - first + 1
	earned := sumByPeriod(earnedDates, earnedAmounts, periodMonths, first, count)
	losses := sumByPeriod(lossDates, lossAmounts, periodMonths, first, count)
	ratios := make([]decimal.Decimal, count)
	for slot := range ratios {
		// IsZero tests the value: a total of 0.00 is zero, and dividing by it would panic.
		if earned[slot].IsZero() {
			ratios[slot] = noEarnedPremium
		} else {
			// DivRound divides once and rounds half away from zero, Java's HALF_UP.
			ratios[slot] = losses[slot].DivRound(earned[slot], ratioPlaces)
		}
	}
	return ratios
}

// periodIndex numbers the calendar-aligned blocks of months, counted from January of year 0.
func periodIndex(day time.Time, periodMonths int) int {
	return (day.Year()*12 + int(day.Month()) - 1) / periodMonths
}

func sumByPeriod(dates []time.Time, amounts []decimal.Decimal, periodMonths int, first int, count int) []decimal.Decimal {
	totals := make([]decimal.Decimal, count)
	for slot := range totals {
		totals[slot] = decimal.Zero
	}
	for i, day := range dates {
		slot := periodIndex(day, periodMonths) - first
		if slot >= 0 && slot < count {
			totals[slot] = totals[slot].Add(amounts[i])
		}
	}
	return totals
}
