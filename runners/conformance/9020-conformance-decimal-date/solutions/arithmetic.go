// Conformance reference: exact decimal arithmetic with explicit rounding, and calendar days.

package conformance_decimal_date

import (
	"time"

	"github.com/shopspring/decimal"
)

const (
	cents         = 2
	secondsPerDay = 24 * 60 * 60
)

type DecimalDates struct{}

func NewDecimalDates() *DecimalDates {
	return &DecimalDates{}
}

func (d *DecimalDates) Normalized(value decimal.Decimal) decimal.Decimal {
	return value
}

func (d *DecimalDates) Add(left decimal.Decimal, right decimal.Decimal) decimal.Decimal {
	return left.Add(right)
}

func (d *DecimalDates) Total(values []decimal.Decimal) decimal.Decimal {
	sum := decimal.Zero
	for _, value := range values {
		sum = sum.Add(value)
	}
	return sum
}

// RoundHalfUp: Round rounds half away from zero, Java's HALF_UP.
func (d *DecimalDates) RoundHalfUp(value decimal.Decimal) decimal.Decimal {
	return value.Round(cents)
}

// RoundHalfEven: RoundBank rounds half to even, Java's HALF_EVEN.
func (d *DecimalDates) RoundHalfEven(value decimal.Decimal) decimal.Decimal {
	return value.RoundBank(cents)
}

// Prorate divides once, exactly, rounding half away from zero: Div would round to
// DivisionPrecision places first and Round would then round a second time.
func (d *DecimalDates) Prorate(premium decimal.Decimal, days int, totalDays int) decimal.Decimal {
	share := premium.Mul(decimal.NewFromInt(int64(days)))
	return share.DivRound(decimal.NewFromInt(int64(totalDays)), cents)
}

func (d *DecimalDates) AddDays(day time.Time, days int) time.Time {
	return day.AddDate(0, 0, days)
}

// DaysBetween counts whole days through Unix seconds: Sub returns a Duration, which cannot hold
// more than about 292 years.
func (d *DecimalDates) DaysBetween(start time.Time, end time.Time) int {
	return int((end.Unix() - start.Unix()) / secondsPerDay)
}
