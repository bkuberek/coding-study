package endorsement_replay

import (
	"slices"
	"sort"
	"time"

	"github.com/shopspring/decimal"
)

const (
	cents         = 2
	secondsPerDay = 24 * 60 * 60
)

var outsideTerm = decimal.NewFromInt(-1)

type EndorsedPolicy struct {
	termStart time.Time
	termEnd   time.Time
	termDays  int64
	// Parallel slices, strictly ascending by effective date: premiums[i] is the full-term premium
	// in force from dates[i] until the next date. There is no sorted map in the standard library.
	dates    []time.Time
	premiums []decimal.Decimal
}

func NewEndorsedPolicy(termStart time.Time, termEnd time.Time, fullTermPremium decimal.Decimal) *EndorsedPolicy {
	return &EndorsedPolicy{
		termStart: termStart,
		termEnd:   termEnd,
		termDays:  daysBetween(termStart, termEnd),
		dates:     []time.Time{termStart},
		premiums:  []decimal.Decimal{fullTermPremium},
	}
}

func (p *EndorsedPolicy) Endorse(effectiveDate time.Time, fullTermPremium decimal.Decimal) bool {
	if !p.inTerm(effectiveDate) {
		return false
	}
	slot, found := slices.BinarySearchFunc(p.dates, effectiveDate, time.Time.Compare)
	if found {
		p.premiums[slot] = fullTermPremium // same date: the later endorsement corrects it
	} else {
		p.dates = slices.Insert(p.dates, slot, effectiveDate)
		p.premiums = slices.Insert(p.premiums, slot, fullTermPremium)
	}
	return true
}

func (p *EndorsedPolicy) PremiumOn(onDate time.Time) decimal.Decimal {
	if !p.inTerm(onDate) {
		return outsideTerm
	}
	// The entry in force is the last one on or before the day; the first date is termStart.
	slot := sort.Search(len(p.dates), func(i int) bool { return p.dates[i].After(onDate) }) - 1
	return p.premiums[slot]
}

func (p *EndorsedPolicy) WrittenPremium() decimal.Decimal {
	return p.EarnedPremium(p.termEnd)
}

func (p *EndorsedPolicy) EarnedPremium(asOfDate time.Time) decimal.Decimal {
	cutoff := asOfDate
	if cutoff.Before(p.termStart) {
		cutoff = p.termStart
	}
	if cutoff.After(p.termEnd) {
		cutoff = p.termEnd
	}
	weighted := decimal.Zero // sum of premium * days over the segments before the cutoff, exact
	for i, start := range p.dates {
		if !start.Before(cutoff) {
			break
		}
		end := p.termEnd
		if i+1 < len(p.dates) {
			end = p.dates[i+1]
		}
		stop := end
		if cutoff.Before(end) {
			stop = cutoff
		}
		weighted = weighted.Add(p.premiums[i].Mul(decimal.NewFromInt(daysBetween(start, stop))))
	}
	// DivRound divides once and rounds half away from zero, Java's HALF_UP.
	return weighted.DivRound(decimal.NewFromInt(p.termDays), cents)
}

// inTerm reports whether the day lies in [termStart, termEnd).
func (p *EndorsedPolicy) inTerm(day time.Time) bool {
	return !day.Before(p.termStart) && day.Before(p.termEnd)
}

// daysBetween counts whole days through Unix seconds: both dates are midnight UTC, and
// Time.Sub returns a Duration, which cannot hold more than about 292 years.
func daysBetween(start time.Time, end time.Time) int64 {
	return (end.Unix() - start.Unix()) / secondsPerDay
}
