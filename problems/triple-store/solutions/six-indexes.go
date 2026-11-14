package triple_store

import (
	"sort"
	"strings"
)

const (
	open    int64 = 1<<53 - 1
	current int64 = open - 1
	huge          = 1_000_000_000_000_000
	sep           = "\x00"
)

type span struct {
	start, end int64
	names      []string
	times      []int64
}

type found struct {
	row  []string
	used []int
}

type match struct {
	ends []string
	id   int
}

// opt is a term that may be missing: a wildcard or a variable that is still free.
type opt struct {
	value string
	ok    bool
}

// TripleStore gives every triple ever recorded a number and a list of spans, the periods during
// which it was present. Six hash indexes list the numbers by subject, predicate, object and the
// three pairs, and one more finds a whole triple, so any pattern with a bound position starts
// from a short list instead of a scan. Removing a triple only closes its span, so the history
// stays.
//
// A query joins its patterns one at a time, always taking the pattern whose candidate list is
// shortest under the variables bound so far, and a path is a breadth-first walk with a visited
// set, so a cycle ends the walk.
type TripleStore struct {
	triples [][3]string
	spans   [][]*span
	exact   map[string]int
	byS     map[string][]int
	byP     map[string][]int
	byO     map[string][]int
	bySP    map[string][]int
	byPO    map[string][]int
	bySO    map[string][]int
	now     int64
	live    int
}

func NewTripleStore() *TripleStore {
	return &TripleStore{
		exact: map[string]int{},
		byS:   map[string][]int{},
		byP:   map[string][]int{},
		byO:   map[string][]int{},
		bySP:  map[string][]int{},
		byPO:  map[string][]int{},
		bySO:  map[string][]int{},
	}
}

// Level 1
func (t *TripleStore) Add(subject string, predicate string, obj string) bool {
	return t.Record(subject, predicate, obj, "", t.now)
}

func (t *TripleStore) Remove(subject string, predicate string, obj string) bool {
	return t.Retract(subject, predicate, obj, t.now)
}

func (t *TripleStore) Size() int {
	return t.live
}

func (t *TripleStore) Match(subject string, predicate string, obj string) [][]string {
	ids, all := t.candidates(term(subject), term(predicate), term(obj))
	hits := [][3]string{}
	for _, id := range t.each(ids, all) {
		if t.present(id, current) {
			hits = append(hits, t.triples[id])
		}
	}
	sort.Slice(hits, func(i, j int) bool { return compareRows(hits[i][:], hits[j][:]) < 0 })
	answer := make([][]string, 0, len(hits))
	for _, hit := range hits {
		answer = append(answer, []string{hit[0], hit[1], hit[2]})
	}
	return answer
}

// Level 2 and 3
func (t *TripleStore) Query(patterns [][]string, columns []string) [][]string {
	rows, _ := t.rows(patterns, columns, current, false)
	return rows
}

// Level 4
func (t *TripleStore) Record(subject string, predicate string, obj string, source string, time int64) bool {
	t.now = time
	key := strings.Join([]string{subject, predicate, obj}, sep)
	id, known := t.exact[key]
	if !known {
		id = t.create(subject, predicate, obj, key)
	}
	history := t.spans[id]
	if n := len(history); n > 0 && history[n-1].end == open {
		last := history[n-1]
		if source != "" && !contains(last.names, source) {
			last.names = append(last.names, source)
			last.times = append(last.times, time)
		}
		return false
	}
	fresh := &span{start: time, end: open}
	if source != "" {
		fresh.names = []string{source}
		fresh.times = []int64{time}
	}
	t.spans[id] = append(history, fresh)
	t.live++
	return true
}

func (t *TripleStore) Retract(subject string, predicate string, obj string, time int64) bool {
	t.now = time
	id, known := t.exact[strings.Join([]string{subject, predicate, obj}, sep)]
	if !known {
		return false
	}
	history := t.spans[id]
	last := history[len(history)-1]
	if last.end != open {
		return false
	}
	last.end = time
	t.live--
	return true
}

func (t *TripleStore) QueryAsOf(patterns [][]string, columns []string, time int64) [][]string {
	rows, _ := t.rows(patterns, columns, time, false)
	return rows
}

func (t *TripleStore) SourcesAsOf(patterns [][]string, columns []string, time int64) [][]string {
	_, sources := t.rows(patterns, columns, time, true)
	return sources
}

// Storage
func (t *TripleStore) create(subject, predicate, obj, key string) int {
	id := len(t.triples)
	t.triples = append(t.triples, [3]string{subject, predicate, obj})
	t.spans = append(t.spans, nil)
	t.exact[key] = id
	t.byS[subject] = append(t.byS[subject], id)
	t.byP[predicate] = append(t.byP[predicate], id)
	t.byO[obj] = append(t.byO[obj], id)
	t.bySP[subject+sep+predicate] = append(t.bySP[subject+sep+predicate], id)
	t.byPO[predicate+sep+obj] = append(t.byPO[predicate+sep+obj], id)
	t.bySO[subject+sep+obj] = append(t.bySO[subject+sep+obj], id)
	return id
}

func (t *TripleStore) spanAt(id int, when int64) *span {
	history := t.spans[id]
	for at := len(history) - 1; at >= 0; at-- {
		if history[at].start <= when {
			if when < history[at].end {
				return history[at]
			}
			return nil
		}
	}
	return nil
}

func (t *TripleStore) present(id int, when int64) bool {
	return t.spanAt(id, when) != nil
}

func term(token string) opt {
	return opt{token, token != "?"}
}

// candidates returns the numbers of the triples that can match, from the narrowest index that
// applies; all is true when every triple can.
func (t *TripleStore) candidates(s, p, o opt) (ids []int, all bool) {
	switch {
	case s.ok && p.ok && o.ok:
		if id, known := t.exact[strings.Join([]string{s.value, p.value, o.value}, sep)]; known {
			return []int{id}, false
		}
		return nil, false
	case s.ok && p.ok:
		return t.bySP[s.value+sep+p.value], false
	case p.ok && o.ok:
		return t.byPO[p.value+sep+o.value], false
	case s.ok && o.ok:
		return t.bySO[s.value+sep+o.value], false
	case s.ok:
		return t.byS[s.value], false
	case p.ok:
		return t.byP[p.value], false
	case o.ok:
		return t.byO[o.value], false
	}
	return nil, true
}

func (t *TripleStore) count(ids []int, all bool) int {
	if all {
		return len(t.triples)
	}
	return len(ids)
}

func (t *TripleStore) each(ids []int, all bool) []int {
	if !all {
		return ids
	}
	every := make([]int, len(t.triples))
	for id := range every {
		every[id] = id
	}
	return every
}

// Queries
func (t *TripleStore) rows(patterns [][]string, columns []string, when int64, track bool) ([][]string, [][]string) {
	hits := []found{}
	t.search(patterns, map[string]string{}, []int{}, columns, when, track, &hits)
	distinct := map[string][]string{}
	for _, one := range hits {
		distinct[strings.Join(one.row, sep)] = one.row
	}
	rows := make([][]string, 0, len(distinct))
	for _, row := range distinct {
		rows = append(rows, row)
	}
	sort.Slice(rows, func(i, j int) bool { return compareRows(rows[i], rows[j]) < 0 })
	if !track {
		return rows, nil
	}
	byRow := map[string]map[string]bool{}
	for _, row := range rows {
		byRow[strings.Join(row, sep)] = map[string]bool{}
	}
	for _, one := range hits {
		names := byRow[strings.Join(one.row, sep)]
		for _, id := range one.used {
			home := t.spanAt(id, when)
			if home == nil {
				continue
			}
			for index, name := range home.names {
				if home.times[index] <= when {
					names[name] = true
				}
			}
		}
	}
	sources := make([][]string, 0, len(rows))
	for _, row := range rows {
		list := []string{}
		for name := range byRow[strings.Join(row, sep)] {
			list = append(list, name)
		}
		sort.Strings(list)
		sources = append(sources, list)
	}
	return rows, sources
}

func (t *TripleStore) search(remaining [][]string, bindings map[string]string, used []int, columns []string, when int64, track bool, hits *[]found) {
	if len(remaining) == 0 {
		row := make([]string, len(columns))
		for index, name := range columns {
			row[index] = bindings[name]
		}
		kept := []int{}
		if track {
			kept = append(kept, used...)
		}
		*hits = append(*hits, found{row, kept})
		return
	}
	best, bestCost := 0, int64(1<<62)
	for at, pattern := range remaining {
		if cost := t.cost(pattern, bindings); cost < bestCost {
			best, bestCost = at, cost
		}
	}
	pattern := remaining[best]
	rest := make([][]string, 0, len(remaining)-1)
	rest = append(rest, remaining[:best]...)
	rest = append(rest, remaining[best+1:]...)
	for _, one := range t.matches(pattern, bindings, when) {
		undo := []string{}
		if unify(pattern, one.ends, bindings, &undo) {
			next := used
			if one.id >= 0 {
				next = append(used, one.id)
			}
			t.search(rest, bindings, next, columns, when, track, hits)
		}
		for _, name := range undo {
			delete(bindings, name)
		}
	}
}

func value(token string, bindings map[string]string) opt {
	if token == "?" {
		return opt{}
	}
	if strings.HasPrefix(token, "?") {
		bound, ok := bindings[token]
		return opt{bound, ok}
	}
	return opt{token, true}
}

func unify(pattern []string, ends []string, bindings map[string]string, undo *[]string) bool {
	tokens := pattern
	if len(ends) == 2 {
		tokens = []string{pattern[0], pattern[2]}
	}
	for at, token := range tokens {
		if token == "?" {
			continue
		}
		if !strings.HasPrefix(token, "?") {
			if token != ends[at] {
				return false
			}
		} else if bound, ok := bindings[token]; ok {
			if bound != ends[at] {
				return false
			}
		} else {
			bindings[token] = ends[at]
			*undo = append(*undo, token)
		}
	}
	return true
}

func (t *TripleStore) cost(pattern []string, bindings map[string]string) int64 {
	s, p, o := value(pattern[0], bindings), value(pattern[1], bindings), value(pattern[2], bindings)
	if strings.HasSuffix(pattern[1], "+") {
		if !s.ok && !o.ok {
			return huge
		}
		return int64(len(t.byP[strings.TrimSuffix(pattern[1], "+")]))
	}
	return int64(t.count(t.candidates(s, p, o)))
}

func (t *TripleStore) matches(pattern []string, bindings map[string]string, when int64) []match {
	s, p, o := value(pattern[0], bindings), value(pattern[1], bindings), value(pattern[2], bindings)
	hits := []match{}
	if strings.HasSuffix(pattern[1], "+") {
		for _, pair := range t.pathPairs(s, strings.TrimSuffix(pattern[1], "+"), o, when) {
			hits = append(hits, match{pair, -1})
		}
		return hits
	}
	ids, all := t.candidates(s, p, o)
	for _, id := range t.each(ids, all) {
		if t.present(id, when) {
			triple := t.triples[id]
			hits = append(hits, match{[]string{triple[0], triple[1], triple[2]}, id})
		}
	}
	return hits
}

func (t *TripleStore) pathPairs(s opt, p string, o opt, when int64) [][]string {
	pairs := [][]string{}
	if s.ok {
		reached := t.reach(s.value, p, true, when)
		if o.ok {
			if reached[o.value] {
				pairs = append(pairs, []string{s.value, o.value})
			}
			return pairs
		}
		for node := range reached {
			pairs = append(pairs, []string{s.value, node})
		}
		return pairs
	}
	if o.ok {
		for node := range t.reach(o.value, p, false, when) {
			pairs = append(pairs, []string{node, o.value})
		}
		return pairs
	}
	starts := map[string]bool{}
	for _, id := range t.byP[p] {
		if t.present(id, when) {
			starts[t.triples[id][0]] = true
		}
	}
	for start := range starts {
		for node := range t.reach(start, p, true, when) {
			pairs = append(pairs, []string{start, node})
		}
	}
	return pairs
}

// reach is the set of nodes at the end of one or more hops; the start is in it only through a cycle.
func (t *TripleStore) reach(start, p string, forward bool, when int64) map[string]bool {
	seen := map[string]bool{}
	queue := []string{start}
	for next := 0; next < len(queue); next++ {
		node := queue[next]
		var ids []int
		if forward {
			ids = t.bySP[node+sep+p]
		} else {
			ids = t.byPO[p+sep+node]
		}
		for _, id := range ids {
			if !t.present(id, when) {
				continue
			}
			following := t.triples[id][0]
			if forward {
				following = t.triples[id][2]
			}
			if !seen[following] {
				seen[following] = true
				queue = append(queue, following)
			}
		}
	}
	return seen
}

func compareRows(a, b []string) int {
	for at := range a {
		if order := strings.Compare(a[at], b[at]); order != 0 {
			return order
		}
	}
	return 0
}

func contains(list []string, item string) bool {
	for _, known := range list {
		if known == item {
			return true
		}
	}
	return false
}
