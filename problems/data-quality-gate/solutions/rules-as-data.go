package data_quality_gate

import (
	"fmt"
	"math"
	"sort"
	"strconv"
	"strings"
)

const emptyShare = 0.0001

var rowChecks = map[string]bool{"not-null": true, "type": true, "allowed": true, "range": true, "unique": true, "references": true}
var batchChecks = map[string]bool{"row-count": true, "drift": true, "freshness": true}
var actions = map[string]bool{"warn": true, "quarantine": true, "block": true}
var daysInMonth = []int{31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31}

func allDigits(text string) bool {
	for _, ch := range text {
		if ch < '0' || ch > '9' {
			return false
		}
	}
	return true
}

func isInt(text string) bool {
	digits := strings.TrimPrefix(text, "-")
	return len(digits) >= 1 && len(digits) <= 15 && allDigits(digits)
}

func isDate(text string) bool {
	if len(text) != 10 || text[4] != '-' || text[7] != '-' {
		return false
	}
	yearText, monthText, dayText := text[0:4], text[5:7], text[8:10]
	if !allDigits(yearText) || !allDigits(monthText) || !allDigits(dayText) {
		return false
	}
	year, _ := strconv.Atoi(yearText)
	month, _ := strconv.Atoi(monthText)
	day, _ := strconv.Atoi(dayText)
	if year < 1 || month < 1 || month > 12 {
		return false
	}
	leap := year%4 == 0 && (year%100 != 0 || year%400 == 0)
	last := daysInMonth[month-1]
	if month == 2 && leap {
		last = 29
	}
	return day >= 1 && day <= last
}

// tenThousandths reads a non-negative decimal with at most four places in units of 0.0001.
func tenThousandths(decimal string) int64 {
	whole, fraction, _ := strings.Cut(decimal, ".")
	wholeValue, _ := strconv.ParseInt(whole, 10, 64)
	fractionValue, _ := strconv.ParseInt((fraction + "0000")[:4], 10, 64)
	return wholeValue*10000 + fractionValue
}

type rule struct {
	ruleID  string
	check   string
	columns []string
	params  []string
	action  string
}

type columnFailures struct {
	column string
	bad    []int
}

// QualityGate keeps rules as data: each one is a check name, its columns and its parameters, in
// the order they were added. Validation runs every rule over the rows and reports what failed; the
// gate runs the row rules first, sets aside the rows that quarantine rules reject, and runs the
// batch rules on what is left.
type QualityGate struct {
	index      map[string]int
	rules      []*rule
	byID       map[string]*rule
	dimensions map[string]map[string]bool
	previous   [][]string
	hasPrev    bool
	now        int64
	aside      []int
}

func NewQualityGate(columns []string) *QualityGate {
	g := &QualityGate{
		index:      map[string]int{},
		byID:       map[string]*rule{},
		dimensions: map[string]map[string]bool{},
		aside:      []int{},
	}
	for at, name := range columns {
		g.index[name] = at
	}
	return g
}

// Level 1
func (g *QualityGate) AddRule(ruleID string, check string, columns []string, params []string) bool {
	if _, used := g.byID[ruleID]; used || (!rowChecks[check] && !batchChecks[check]) {
		return false
	}
	for _, column := range columns {
		if _, known := g.index[column]; !known {
			return false
		}
	}
	if check == "references" {
		if _, loaded := g.dimensions[params[0]]; !loaded {
			return false
		}
	}
	r := &rule{ruleID, check, append([]string{}, columns...), append([]string{}, params...), "block"}
	g.rules = append(g.rules, r)
	g.byID[ruleID] = r
	return true
}

func (g *QualityGate) Validate(rows [][]string) [][]string {
	report := [][]string{}
	for _, r := range g.rules {
		report = append(report, g.findings(r, rows)...)
	}
	return report
}

func (g *QualityGate) FailingRows(rows [][]string, ruleID string) []int {
	r, known := g.byID[ruleID]
	if !known || batchChecks[r.check] {
		return []int{}
	}
	seen := map[int]bool{}
	failing := []int{}
	for _, entry := range g.rowFailures(r, rows) {
		for _, at := range entry.bad {
			if !seen[at] {
				seen[at] = true
				failing = append(failing, at)
			}
		}
	}
	sort.Ints(failing)
	return failing
}

// Level 2
func (g *QualityGate) LoadDimension(name string, keys []string) int {
	set := map[string]bool{}
	for _, key := range keys {
		set[key] = true
	}
	g.dimensions[name] = set
	return len(set)
}

func (g *QualityGate) SetPreviousBatch(rows [][]string) int {
	g.previous = rows
	g.hasPrev = true
	return len(rows)
}

// Level 3
func (g *QualityGate) SetTime(now int64) {
	g.now = now
}

// Level 4
func (g *QualityGate) SetAction(ruleID string, action string) bool {
	r, known := g.byID[ruleID]
	if !known || !actions[action] || (action == "quarantine" && batchChecks[r.check]) {
		return false
	}
	r.action = action
	return true
}

func (g *QualityGate) Decide(rows [][]string) [][]string {
	setAside := map[int]bool{}
	for _, r := range g.rules {
		if rowChecks[r.check] && r.action == "quarantine" {
			for _, at := range g.FailingRows(rows, r.ruleID) {
				setAside[at] = true
			}
		}
	}
	kept := [][]string{}
	for at, row := range rows {
		if !setAside[at] {
			kept = append(kept, row)
		}
	}
	findings := [][]string{}
	blocked := false
	for _, r := range g.rules {
		seen := kept
		if rowChecks[r.check] {
			seen = rows
		}
		for _, entry := range g.findings(r, seen) {
			findings = append(findings, append(entry, r.action))
			blocked = blocked || r.action == "block"
		}
	}
	if blocked {
		g.aside = []int{}
		return append([][]string{{"block", "0", "0"}}, findings...)
	}
	g.aside = []int{}
	for at := range setAside {
		g.aside = append(g.aside, at)
	}
	sort.Ints(g.aside)
	g.previous = kept
	g.hasPrev = true
	head := []string{"publish", strconv.Itoa(len(kept)), strconv.Itoa(len(setAside))}
	return append([][]string{head}, findings...)
}

func (g *QualityGate) Quarantined() []int {
	return append([]int{}, g.aside...)
}

// Helpers
func (g *QualityGate) findings(r *rule, rows [][]string) [][]string {
	found := [][]string{}
	if rowChecks[r.check] {
		for _, entry := range g.rowFailures(r, rows) {
			if len(entry.bad) > 0 {
				found = append(found, []string{r.ruleID, entry.column, strconv.Itoa(len(entry.bad))})
			}
		}
		return found
	}
	if observed, failed := g.batchFailure(r, rows); failed {
		found = append(found, []string{r.ruleID, strings.Join(r.columns, ""), observed})
	}
	return found
}

// rowFailures gives, for each column of a row rule (one joined key for unique), the rows that fail it.
func (g *QualityGate) rowFailures(r *rule, rows [][]string) []columnFailures {
	if r.check == "unique" {
		groups := map[string][]int{}
		for at, row := range rows {
			var key strings.Builder
			hasNull := false
			for _, column := range r.columns {
				part := row[g.index[column]]
				hasNull = hasNull || part == ""
				fmt.Fprintf(&key, "%d:%s", len(part), part)
			}
			if !hasNull {
				groups[key.String()] = append(groups[key.String()], at)
			}
		}
		bad := []int{}
		for _, group := range groups {
			if len(group) > 1 {
				bad = append(bad, group...)
			}
		}
		sort.Ints(bad)
		return []columnFailures{{strings.Join(r.columns, "+"), bad}}
	}
	failures := []columnFailures{}
	for _, column := range r.columns {
		at := g.index[column]
		bad := []int{}
		for number, row := range rows {
			if g.fails(r, row[at]) {
				bad = append(bad, number)
			}
		}
		failures = append(failures, columnFailures{column, bad})
	}
	return failures
}

func (g *QualityGate) fails(r *rule, value string) bool {
	if r.check == "not-null" {
		return value == ""
	}
	if value == "" {
		return false
	}
	switch r.check {
	case "type":
		if r.params[0] == "int" {
			return !isInt(value)
		}
		return !isDate(value)
	case "allowed":
		for _, allowed := range r.params {
			if allowed == value {
				return false
			}
		}
		return true
	case "range":
		if !isInt(value) {
			return false
		}
		number, _ := strconv.ParseInt(value, 10, 64)
		low, _ := strconv.ParseInt(r.params[0], 10, 64)
		high, _ := strconv.ParseInt(r.params[1], 10, 64)
		return number < low || number > high
	default:
		return !g.dimensions[r.params[0]][value]
	}
}

// batchFailure gives the observed value of a failing batch rule, and whether it failed.
func (g *QualityGate) batchFailure(r *rule, rows [][]string) (string, bool) {
	if r.check == "row-count" {
		if !g.hasPrev {
			return "", false
		}
		before := int64(len(g.previous))
		tolerance, _ := strconv.ParseInt(r.params[0], 10, 64)
		low := before * (100 - tolerance) / 100
		high := (before*(100+tolerance) + 99) / 100
		count := int64(len(rows))
		return strconv.Itoa(len(rows)), count < low || count > high
	}
	column := g.index[r.columns[0]]
	values := integers(rows, column)
	if r.check == "freshness" {
		if len(values) == 0 {
			return "none", true
		}
		newest := values[0]
		for _, value := range values {
			if value > newest {
				newest = value
			}
		}
		limit, _ := strconv.ParseInt(r.params[0], 10, 64)
		lag := g.now - newest
		return strconv.FormatInt(lag, 10), lag > limit
	}
	if !g.hasPrev {
		return "", false
	}
	baseline := integers(g.previous, column)
	if len(values) == 0 || len(baseline) == 0 {
		return "", false
	}
	edges := make([]int64, 0, len(r.params)-1)
	for _, edge := range r.params[1:] {
		value, _ := strconv.ParseInt(edge, 10, 64)
		edges = append(edges, value)
	}
	units := int64(math.Floor(psi(values, baseline, edges)*10000 + 0.5))
	if units < tenThousandths(r.params[0]) {
		return "", false
	}
	return fmt.Sprintf("%d.%04d", units/10000, units%10000), true
}

func integers(rows [][]string, column int) []int64 {
	values := []int64{}
	for _, row := range rows {
		if isInt(row[column]) {
			value, _ := strconv.ParseInt(row[column], 10, 64)
			values = append(values, value)
		}
	}
	return values
}

func psi(values []int64, baseline []int64, edges []int64) float64 {
	actual := shares(values, edges)
	expected := shares(baseline, edges)
	total := 0.0
	for bin := range actual {
		total += (actual[bin] - expected[bin]) * math.Log(actual[bin]/expected[bin])
	}
	return total
}

func shares(sample []int64, edges []int64) []float64 {
	counts := make([]int, len(edges)+1)
	for _, value := range sample {
		bin := sort.Search(len(edges), func(i int) bool { return edges[i] > value })
		counts[bin]++
	}
	result := make([]float64, len(counts))
	for bin, count := range counts {
		if count == 0 {
			result[bin] = emptyShare
		} else {
			result[bin] = float64(count) / float64(len(sample))
		}
	}
	return result
}
