package earned_premium_as_of

import (
	"time"

	"github.com/shopspring/decimal"
)

const (
	cents         = 2
	secondsPerDay = 24 * 60 * 60
)

func earnedPremium(premiums []decimal.Decimal, terms [][]time.Time, valuationDate time.Time) decimal.Decimal {
	total := decimal.Zero
	for i, premium := range premiums {
		termDays := daysBetween(terms[i][0], terms[i][1])
		earnedDays := min(max(daysBetween(terms[i][0], valuationDate), 0), termDays)
		// Each policy is rounded to cents on its own; the book total is the sum of rounded
		// amounts. DivRound divides once and rounds half away from zero, Java's HALF_UP.
		earned := premium.Mul(decimal.NewFromInt(earnedDays)).DivRound(decimal.NewFromInt(termDays), cents)
		total = total.Add(earned)
	}
	return total
}

// daysBetween counts whole days through Unix seconds: both dates are midnight UTC, and
// Time.Sub returns a Duration, which cannot hold more than about 292 years.
func daysBetween(start time.Time, end time.Time) int64 {
	return (end.Unix() - start.Unix()) / secondsPerDay
}
