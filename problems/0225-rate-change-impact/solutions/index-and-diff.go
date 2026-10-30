package rate_change_impact

import (
	"slices"
	"strings"

	"github.com/shopspring/decimal"
)

const percentPlaces = 2

type change struct {
	code    string
	percent decimal.Decimal
}

func rateChangeImpact(oldCodes []string, oldRates []decimal.Decimal, newCodes []string, newRates []decimal.Decimal) [][]string {
	old := make(map[string]decimal.Decimal, len(oldCodes))
	for i, code := range oldCodes {
		old[code] = oldRates[i]
	}
	current := make(map[string]decimal.Decimal, len(newCodes))
	for i, code := range newCodes {
		current[code] = newRates[i]
	}

	var changed []change
	var added, removed []string
	for code, rate := range current {
		before, existed := old[code]
		if !existed {
			added = append(added, code)
		} else if !rate.Equal(before) { // value equality: 12.50 equals 12.5
			// DivRound divides once and rounds half away from zero, Java's HALF_UP.
			percent := rate.Sub(before).Mul(decimal.NewFromInt(100)).DivRound(before, percentPlaces)
			changed = append(changed, change{code: code, percent: percent})
		}
	}
	for code := range old {
		if _, kept := current[code]; !kept {
			removed = append(removed, code)
		}
	}

	// Numeric order of the rounded percent, largest first; ties by code in byte order.
	slices.SortFunc(changed, func(a, b change) int {
		if byPercent := b.percent.Cmp(a.percent); byPercent != 0 {
			return byPercent
		}
		return strings.Compare(a.code, b.code)
	})
	slices.Sort(added)
	slices.Sort(removed)

	rows := make([][]string, 0, len(changed)+len(added)+len(removed))
	for _, c := range changed {
		// StringFixed pads to two digits, and a decimal has no negative zero: "0.00", never "-0.00".
		rows = append(rows, []string{c.code, "changed", c.percent.StringFixed(percentPlaces)})
	}
	for _, code := range added {
		rows = append(rows, []string{code, "added", ""})
	}
	for _, code := range removed {
		rows = append(rows, []string{code, "removed", ""})
	}
	return rows
}
