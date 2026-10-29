package runner

import (
	"fmt"
	"math/big"
	"regexp"
	"strings"
	"time"

	"github.com/shopspring/decimal"
)

const (
	firstYear = 1
	lastYear  = 9999
)

var (
	decimalPattern = regexp.MustCompile(`^-?(0|[1-9][0-9]*)(\.[0-9]+)?$`)
	datePattern    = regexp.MustCompile(`^[0-9]{4}-[0-9]{2}-[0-9]{2}$`)
	ten            = big.NewInt(10)
)

// decodeDecimal keeps the input's scale: "2500.00" has exponent -2
// (docs/specs/problem-format.md#decimal-and-date).
func decodeDecimal(value any, t *dslType) (decimal.Decimal, error) {
	text, ok := value.(string)
	if !ok || !decimalPattern.MatchString(text) {
		return decimal.Decimal{}, mismatch(value, t)
	}
	d, err := decimal.NewFromString(text)
	if err != nil {
		return decimal.Decimal{}, mismatch(value, t)
	}
	return d, nil
}

// decodeDate is the day at midnight UTC.
func decodeDate(value any, t *dslType) (time.Time, error) {
	text, ok := value.(string)
	if !ok || !datePattern.MatchString(text) {
		return time.Time{}, mismatch(value, t)
	}
	day, err := time.Parse(time.DateOnly, text)
	if err != nil || day.Year() < firstYear {
		return time.Time{}, &inputError{fmt.Sprintf("%q is not a calendar day", text)}
	}
	return day, nil
}

// canonicalDecimal writes d without trailing fractional zeros and without -0, so equal numbers
// have equal text. It works on the coefficient and exponent: String follows the package settings
// TrimTrailingZeros and UseScientificNotation, which a solution may change.
func canonicalDecimal(d decimal.Decimal) string {
	coefficient, exponent := d.Coefficient(), d.Exponent()
	if coefficient.Sign() == 0 {
		return "0"
	}
	var quotient, remainder big.Int
	for exponent < 0 {
		quotient.QuoRem(coefficient, ten, &remainder)
		if remainder.Sign() != 0 {
			break
		}
		coefficient.Set(&quotient)
		exponent++
	}
	sign := ""
	if coefficient.Sign() < 0 {
		sign = "-"
	}
	digits := new(big.Int).Abs(coefficient).String()
	if exponent >= 0 {
		return sign + digits + strings.Repeat("0", int(exponent))
	}
	places := int(-exponent)
	if len(digits) <= places {
		digits = strings.Repeat("0", places-len(digits)+1) + digits
	}
	point := len(digits) - places
	return sign + digits[:point] + "." + digits[point:]
}

// encodeDate accepts only a day at midnight in time.UTC, in years 1 to 9999: any other time
// would name a different day in another zone.
func encodeDate(day time.Time) (any, error) {
	if day.Location() != time.UTC {
		return nil, &invalidOutput{fmt.Sprintf("date must be in time.UTC, got %s in %s", day.Format(time.DateTime), day.Location())}
	}
	if day.Hour() != 0 || day.Minute() != 0 || day.Second() != 0 || day.Nanosecond() != 0 {
		return nil, &invalidOutput{fmt.Sprintf("date must be at midnight, got %s", day.Format(time.RFC3339Nano))}
	}
	if day.Year() < firstYear || day.Year() > lastYear {
		return nil, &invalidOutput{fmt.Sprintf("date out of range: %s", day.Format(time.DateOnly))}
	}
	return day.Format(time.DateOnly), nil
}

// freshDecimalSettings restores shopspring/decimal's package settings to their defaults before
// every case, as the Python runner gives every case a fresh decimal context: a solution that
// sets DivisionPrecision cannot change a later case, or another target in the same process.
func freshDecimalSettings() {
	decimal.DivisionPrecision = 16
	decimal.PowPrecisionNegativeExponent = 16
	decimal.MarshalJSONWithoutQuotes = false
	decimal.TrimTrailingZeros = true
	decimal.UseScientificNotation = false
	decimal.ExpMaxIterations = 1000
	decimal.MaxDecodeExponent = 10000
}
