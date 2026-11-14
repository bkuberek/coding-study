package pro_rata_unearned_premium

import (
	"time"

	"github.com/shopspring/decimal"
)

const (
	cents         = 2
	secondsPerDay = 24 * 60 * 60
)

var outsideTerm = decimal.NewFromInt(-1)

func unearnedPremium(termPremium decimal.Decimal, termStart time.Time, termEnd time.Time, changeDate time.Time) decimal.Decimal {
	if changeDate.Before(termStart) || changeDate.After(termEnd) {
		return outsideTerm
	}
	remaining := daysBetween(changeDate, termEnd)
	termDays := daysBetween(termStart, termEnd)
	// DivRound divides once, exactly, and rounds half away from zero (Java's HALF_UP); Div would
	// round to DivisionPrecision places first, and the cents rounding would then be a second one.
	return termPremium.Mul(decimal.NewFromInt(remaining)).DivRound(decimal.NewFromInt(termDays), cents)
}

// daysBetween counts whole days through Unix seconds: both dates are midnight UTC, and
// Time.Sub returns a Duration, which cannot hold more than about 292 years.
func daysBetween(start time.Time, end time.Time) int64 {
	return (end.Unix() - start.Unix()) / secondsPerDay
}
