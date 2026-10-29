// Conformance: decimal and date round-trip. Statement: .statements/conformance-decimal-date-types.md. Run: cstudy test conformance-decimal-date-types

package conformance_decimal_date_types

import (
	"time"

	"github.com/shopspring/decimal"
)

type TypeEcho struct{}

func NewTypeEcho(label string) *TypeEcho {
	return &TypeEcho{}
}

func (e *TypeEcho) EchoDecimal(value decimal.Decimal) decimal.Decimal {
	panic("not implemented")
}

func (e *TypeEcho) EchoDate(value time.Time) time.Time {
	panic("not implemented")
}

func (e *TypeEcho) EchoDecimalArray(value []decimal.Decimal) []decimal.Decimal {
	panic("not implemented")
}

func (e *TypeEcho) EchoDateArray(value []time.Time) []time.Time {
	panic("not implemented")
}

func (e *TypeEcho) EchoDecimalMatrix(value [][]decimal.Decimal) [][]decimal.Decimal {
	panic("not implemented")
}

func (e *TypeEcho) EchoDateMatrix(value [][]time.Time) [][]time.Time {
	panic("not implemented")
}

func (e *TypeEcho) EchoDecimalList(value []decimal.Decimal) []decimal.Decimal {
	panic("not implemented")
}

func (e *TypeEcho) EchoDateList(value []time.Time) []time.Time {
	panic("not implemented")
}
