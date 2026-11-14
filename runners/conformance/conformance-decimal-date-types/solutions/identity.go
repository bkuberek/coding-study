// Conformance reference: every echo method returns its decimal or date argument unchanged.

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
	return value
}

func (e *TypeEcho) EchoDate(value time.Time) time.Time {
	return value
}

func (e *TypeEcho) EchoDecimalArray(value []decimal.Decimal) []decimal.Decimal {
	return value
}

func (e *TypeEcho) EchoDateArray(value []time.Time) []time.Time {
	return value
}

func (e *TypeEcho) EchoDecimalMatrix(value [][]decimal.Decimal) [][]decimal.Decimal {
	return value
}

func (e *TypeEcho) EchoDateMatrix(value [][]time.Time) [][]time.Time {
	return value
}

func (e *TypeEcho) EchoDecimalList(value []decimal.Decimal) []decimal.Decimal {
	return value
}

func (e *TypeEcho) EchoDateList(value []time.Time) []time.Time {
	return value
}
