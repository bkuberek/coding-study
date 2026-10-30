package installment_schedule

import (
	"time"

	"github.com/shopspring/decimal"
)

const cents = 2

func installmentSchedule(premium decimal.Decimal, installmentCount int, firstDueDate time.Time) [][]string {
	schedule := make([][]string, installmentCount)
	if installmentCount == 0 {
		return schedule
	}
	totalCents := premium.Shift(cents).IntPart() // exact: at most two fractional digits
	base := totalCents / int64(installmentCount)
	leftover := totalCents % int64(installmentCount)
	for number := range schedule {
		// Leftover cents go to the first installments.
		amount := base
		if int64(number) < leftover {
			amount++
		}
		due := addMonths(firstDueDate, number)
		schedule[number] = []string{due.Format(time.DateOnly), decimal.New(amount, -cents).StringFixed(cents)}
	}
	return schedule
}

// addMonths counts from the anchor and clamps to the last day of a short month, like Java's
// plusMonths. AddDate(0, n, 0) would normalize 31 January plus one month into 3 March.
func addMonths(anchor time.Time, months int) time.Time {
	index := int(anchor.Month()) - 1 + months
	year := anchor.Year() + index/12
	month := time.Month(index%12 + 1)
	// Day 0 of the next month is the last day of this one.
	lastDay := time.Date(year, month+1, 0, 0, 0, 0, 0, time.UTC).Day()
	return time.Date(year, month, min(anchor.Day(), lastDay), 0, 0, 0, 0, time.UTC)
}
