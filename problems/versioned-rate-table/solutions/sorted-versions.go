package versioned_rate_table

import (
	"slices"
	"sort"
	"time"

	"github.com/shopspring/decimal"
)

var notFound = decimal.NewFromInt(-1)

type version struct {
	id    int
	rates map[string]decimal.Decimal
}

type RateTable struct {
	// Parallel slices sorted by effective date; equal dates stay in publish order.
	dates     []time.Time
	versions  []version
	published int
}

func NewRateTable() *RateTable {
	return &RateTable{}
}

func (t *RateTable) Publish(effectiveDate time.Time, classCodes []string, rates []decimal.Decimal) {
	t.published++
	slot := t.versionsOnOrBefore(effectiveDate)
	// A fresh map, so a published version never changes afterwards.
	table := make(map[string]decimal.Decimal, len(classCodes))
	for i, code := range classCodes {
		table[code] = rates[i]
	}
	t.dates = slices.Insert(t.dates, slot, effectiveDate)
	t.versions = slices.Insert(t.versions, slot, version{id: t.published, rates: table})
}

func (t *RateTable) RateAsOf(onDate time.Time, classCode string) decimal.Decimal {
	slot := t.versionsOnOrBefore(onDate)
	if slot == 0 {
		return notFound
	}
	if rate, ok := t.versions[slot-1].rates[classCode]; ok {
		return rate
	}
	return notFound
}

func (t *RateTable) VersionAsOf(onDate time.Time) int {
	slot := t.versionsOnOrBefore(onDate)
	if slot == 0 {
		return -1
	}
	return t.versions[slot-1].id
}

// versionsOnOrBefore counts the versions effective on or before the day (upper bound).
// sort.Search finds the first version after the day, so equal dates fall on the "before" side.
func (t *RateTable) versionsOnOrBefore(day time.Time) int {
	return sort.Search(len(t.dates), func(i int) bool {
		return t.dates[i].After(day)
	})
}
