package slo_burn_rate

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
)

type slo struct {
	good, total       string
	met, outOf, width int64
}

func (s *slo) spare() int64 { return s.outOf - s.met }

type alert struct {
	severity                   string
	longWindow, shortWindow    int64
	aboveTop, aboveDenominator int64
}

// SloMonitor keeps every counter's samples in time order. The increase over a window walks the
// samples inside it and adds each step, counting a drop as a restart from zero. A histogram is one
// such counter per bucket. SLOs, burn rates and alerts are ratios of increases, kept as exact
// fractions and compared by cross-multiplying.
type SloMonitor struct {
	times  map[string][]int64
	values map[string][]int64
	bounds map[string][]int64
	slos   map[string]*slo
	alerts map[string][]alert
}

func NewSloMonitor() *SloMonitor {
	return &SloMonitor{
		times:  map[string][]int64{},
		values: map[string][]int64{},
		bounds: map[string][]int64{},
		slos:   map[string]*slo{},
		alerts: map[string][]alert{},
	}
}

// Level 1
func (m *SloMonitor) Scrape(series string, timestamp int64, value int64) string {
	seen := m.times[series]
	if len(seen) > 0 && timestamp <= seen[len(seen)-1] {
		return "out-of-order"
	}
	m.times[series] = append(seen, timestamp)
	m.values[series] = append(m.values[series], value)
	return "ok"
}

func (m *SloMonitor) ScrapeSeries(series string, start int64, step int64, values []int64) int {
	stored := 0
	for i, value := range values {
		if m.Scrape(series, start+int64(i)*step, value) == "ok" {
			stored++
		}
	}
	return stored
}

func (m *SloMonitor) Increase(series string, start int64, end int64) int64 {
	_, got := m.window(series, start, end)
	if len(got) < 2 {
		return -1
	}
	total := int64(0)
	for i := 1; i < len(got); i++ {
		if got[i] >= got[i-1] {
			total += got[i] - got[i-1]
		} else {
			total += got[i]
		}
	}
	return total
}

func (m *SloMonitor) Rate(series string, start int64, end int64) string {
	seen, _ := m.window(series, start, end)
	if len(seen) < 2 {
		return ""
	}
	return fraction(m.Increase(series, start, end), seen[len(seen)-1]-seen[0])
}

func (m *SloMonitor) Resets(series string, start int64, end int64) int {
	_, got := m.window(series, start, end)
	drops := 0
	for i := 1; i < len(got); i++ {
		if got[i] < got[i-1] {
			drops++
		}
	}
	return drops
}

// Level 2
func (m *SloMonitor) ScrapeHistogram(name string, timestamp int64, bounds []int64, counts []int64) string {
	seen := m.times[name+":le=inf"]
	if len(seen) > 0 && timestamp <= seen[len(seen)-1] {
		return "out-of-order"
	}
	m.bounds[name] = append([]int64(nil), bounds...)
	for i, bound := range bounds {
		m.Scrape(name+":le="+strconv.FormatInt(bound, 10), timestamp, counts[i])
	}
	m.Scrape(name+":le=inf", timestamp, counts[len(bounds)])
	return "ok"
}

func (m *SloMonitor) FractionWithin(name string, threshold int64, start int64, end int64) string {
	counts := m.buckets(name, start, end)
	if counts == nil {
		return ""
	}
	for i, bound := range m.bounds[name] {
		if bound == threshold {
			return fraction(counts[i], counts[len(counts)-1])
		}
	}
	return ""
}

func (m *SloMonitor) Quantile(name string, q string, start int64, end int64) string {
	counts := m.buckets(name, start, end)
	if counts == nil {
		return ""
	}
	top, bottom := parseFraction(q)
	limits := m.bounds[name]
	total := counts[len(counts)-1]
	// The rank is q * total; the first bucket whose count reaches it holds the quantile.
	index := 0
	for counts[index]*bottom < top*total {
		index++
	}
	if index == len(limits) {
		return strconv.FormatInt(limits[len(limits)-1], 10)
	}
	lower, before := int64(0), int64(0)
	if index > 0 {
		lower, before = limits[index-1], counts[index-1]
	}
	inside := counts[index] - before
	numerator := lower*bottom*inside + (limits[index]-lower)*(top*total-bottom*before)
	return fraction(numerator, bottom*inside)
}

// Level 3
func (m *SloMonitor) DefineSlo(name string, goodSeries string, totalSeries string, objective string, window int64) string {
	if _, taken := m.slos[name]; taken {
		return "duplicate"
	}
	met, outOf := parseFraction(objective)
	if met <= 0 || met >= outOf {
		return "bad-objective"
	}
	m.slos[name] = &slo{goodSeries, totalSeries, met, outOf, window}
	m.alerts[name] = []alert{}
	return "ok"
}

func (m *SloMonitor) Sli(name string, at int64) string {
	s, known := m.slos[name]
	if !known {
		return ""
	}
	bad, total, ok := m.counts(s, at, s.width)
	if !ok {
		return ""
	}
	return fraction(total-bad, total)
}

func (m *SloMonitor) BudgetRemaining(name string, at int64) string {
	s, known := m.slos[name]
	if !known {
		return ""
	}
	numerator, denominator, ok := m.left(s, at)
	if !ok {
		return ""
	}
	return fraction(numerator, denominator)
}

func (m *SloMonitor) BurnRate(name string, at int64, lookback int64) string {
	s, known := m.slos[name]
	if !known {
		return ""
	}
	bad, total, ok := m.counts(s, at, lookback)
	if !ok {
		return ""
	}
	return fraction(bad*s.outOf, total*s.spare())
}

func (m *SloMonitor) TimeToExhaustion(name string, at int64, lookback int64) int64 {
	s, known := m.slos[name]
	if !known {
		return -1
	}
	leftOver, _, ok := m.left(s, at)
	if !ok {
		return -1
	}
	if leftOver <= 0 {
		return 0
	}
	recentBad, recentTotal, ok := m.counts(s, at, lookback)
	if !ok || recentBad == 0 {
		return -1
	}
	bad, total, _ := m.counts(s, at, s.width)
	// remaining * window / burn rate, with every product below 2^63.
	numerator := s.width * (total*s.spare() - bad*s.outOf) * recentTotal
	return numerator / (total * recentBad * s.outOf)
}

// Level 4
func (m *SloMonitor) AddAlert(slo string, severity string, longWindow int64, shortWindow int64, threshold string) string {
	list, known := m.alerts[slo]
	if !known {
		return "unknown-slo"
	}
	for _, a := range list {
		if a.severity == severity {
			return "duplicate"
		}
	}
	if longWindow <= 0 || shortWindow < 0 || shortWindow >= longWindow {
		return "bad-windows"
	}
	top, bottom := parseFraction(threshold)
	m.alerts[slo] = append(list, alert{severity, longWindow, shortWindow, top, bottom})
	return "ok"
}

func (m *SloMonitor) Firing(slo string, at int64) []string {
	found := []string{}
	target, known := m.slos[slo]
	if !known {
		return found
	}
	for _, a := range m.alerts[slo] {
		if m.fires(target, a, at) {
			found = append(found, a.severity)
		}
	}
	return found
}

func (m *SloMonitor) Timeline(slo string, start int64, end int64, step int64) []string {
	events := []string{}
	target, known := m.slos[slo]
	if !known {
		return events
	}
	list := m.alerts[slo]
	state := make([]bool, len(list))
	for at := start; at <= end; at += step {
		for i, a := range list {
			now := m.fires(target, a, at)
			if now != state[i] {
				word := "stop"
				if now {
					word = "start"
				}
				events = append(events, fmt.Sprintf("%d %s %s", at, a.severity, word))
				state[i] = now
			}
		}
	}
	return events
}

// Helpers
func gcd(a, b int64) int64 {
	for b != 0 {
		a, b = b, a%b
	}
	if a < 0 {
		return -a
	}
	return a
}

// fraction writes p/q in lowest terms with q > 0, or p for a whole number.
func fraction(numerator, denominator int64) string {
	if denominator < 0 {
		numerator, denominator = -numerator, -denominator
	}
	common := gcd(numerator, denominator)
	numerator, denominator = numerator/common, denominator/common
	if denominator == 1 {
		return strconv.FormatInt(numerator, 10)
	}
	return strconv.FormatInt(numerator, 10) + "/" + strconv.FormatInt(denominator, 10)
}

func parseFraction(text string) (int64, int64) {
	top, bottom, found := strings.Cut(text, "/")
	p, _ := strconv.ParseInt(top, 10, 64)
	if !found {
		return p, 1
	}
	q, _ := strconv.ParseInt(bottom, 10, 64)
	return p, q
}

// window returns the times and values of the series inside [start, end].
func (m *SloMonitor) window(series string, start, end int64) ([]int64, []int64) {
	seen := m.times[series]
	low := sort.Search(len(seen), func(i int) bool { return seen[i] >= start })
	high := sort.Search(len(seen), func(i int) bool { return seen[i] > end })
	if high < low {
		high = low
	}
	return seen[low:high], m.values[series][low:high]
}

// buckets returns the increase of every bucket over the window, or nil when the window has no
// requests.
func (m *SloMonitor) buckets(name string, start, end int64) []int64 {
	limits, known := m.bounds[name]
	if !known {
		return nil
	}
	counts := make([]int64, 0, len(limits)+1)
	for _, bound := range limits {
		counts = append(counts, m.Increase(name+":le="+strconv.FormatInt(bound, 10), start, end))
	}
	counts = append(counts, m.Increase(name+":le=inf", start, end))
	if counts[len(counts)-1] <= 0 {
		return nil
	}
	return counts
}

// counts returns the bad and total requests over [at - span, at], and false without requests.
func (m *SloMonitor) counts(s *slo, at, span int64) (int64, int64, bool) {
	total := m.Increase(s.total, at-span, at)
	good := m.Increase(s.good, at-span, at)
	if total <= 0 || good < 0 {
		return 0, 0, false
	}
	return total - good, total, true
}

// left returns the share of the budget left as a numerator and a denominator.
func (m *SloMonitor) left(s *slo, at int64) (int64, int64, bool) {
	bad, total, ok := m.counts(s, at, s.width)
	if !ok {
		return 0, 0, false
	}
	return total*s.spare() - bad*s.outOf, total * s.spare(), true
}

func (m *SloMonitor) burnsAbove(s *slo, at, span int64, a alert) bool {
	bad, total, ok := m.counts(s, at, span)
	return ok && bad*s.outOf*a.aboveDenominator > a.aboveTop*total*s.spare()
}

func (m *SloMonitor) fires(s *slo, a alert, at int64) bool {
	if !m.burnsAbove(s, at, a.longWindow, a) {
		return false
	}
	return a.shortWindow == 0 || m.burnsAbove(s, at, a.shortWindow, a)
}
