package iac_plan_engine

import (
	"container/heap"
	"sort"
	"strings"
)

const (
	unknown     = "<unknown>"
	forcesMark  = "forces-replacement"
	createFirst = "create-before-destroy"
	deleteFirst = "destroy-before-create"
)

type step struct {
	verb, address, tag string
	rank               int
	mode               string
	diff               [][]string
	before, after      []*step
	waiting            int
}

// readySteps is a min-heap of steps by rank, then address.
type readySteps []*step

func (r readySteps) Len() int { return len(r) }
func (r readySteps) Less(i, j int) bool {
	if r[i].rank != r[j].rank {
		return r[i].rank < r[j].rank
	}
	return r[i].address < r[j].address
}
func (r readySteps) Swap(i, j int)  { r[i], r[j] = r[j], r[i] }
func (r *readySteps) Push(x any)    { *r = append(*r, x.(*step)) }
func (r *readySteps) Pop() any {
	old := *r
	last := old[len(old)-1]
	*r = old[:len(old)-1]
	return last
}

// PlanEngine keeps desired and actual resources as maps of attributes. A plan resolves the
// references of the desired resources in dependency order, which tells for each resource whether
// it is created, updated, replaced, left alone or deleted, then turns those actions into steps
// joined by before-rules and lists the steps in the smallest order by (rank, address) that keeps
// every rule. Apply walks the same steps, skips those behind a failure, and records the state
// after each step that succeeds.
type PlanEngine struct {
	desired  map[string]map[string]string
	current  map[string]map[string]string
	deps     map[string]map[string]bool
	old      map[string]map[string]string
	oldDeps  map[string]map[string]bool
	forces   map[string]bool
	computed map[string]map[string]bool
	marked   map[string]bool
}

func NewPlanEngine() *PlanEngine {
	return &PlanEngine{
		desired:  map[string]map[string]string{},
		current:  map[string]map[string]string{},
		deps:     map[string]map[string]bool{},
		old:      map[string]map[string]string{},
		oldDeps:  map[string]map[string]bool{},
		forces:   map[string]bool{},
		computed: map[string]map[string]bool{},
		marked:   map[string]bool{},
	}
}

// Level 1

func (e *PlanEngine) Desire(address string, attributes [][]string) bool {
	_, had := e.desired[address]
	e.desired[address] = toMap(attributes)
	return !had
}

func (e *PlanEngine) Remove(address string) bool {
	_, had := e.desired[address]
	delete(e.desired, address)
	return had
}

func (e *PlanEngine) Observe(address string, attributes [][]string) bool {
	_, had := e.current[address]
	e.current[address] = toMap(attributes)
	return !had
}

func (e *PlanEngine) Plan() [][]string {
	errors, steps := e.build()
	if len(errors) > 0 {
		return errors
	}
	rows := [][]string{}
	for _, s := range steps {
		head := []string{s.verb, s.address}
		if s.tag != "" {
			head = append(head, s.tag)
		}
		rows = append(rows, head)
		rows = append(rows, s.diff...)
	}
	return rows
}

// Level 2

func (e *PlanEngine) ObserveDependency(address string, dependsOn string) bool {
	_, a := e.current[address]
	_, b := e.current[dependsOn]
	if !a || !b || e.deps[address][dependsOn] {
		return false
	}
	if e.deps[address] == nil {
		e.deps[address] = map[string]bool{}
	}
	e.deps[address][dependsOn] = true
	return true
}

// Level 3

func (e *PlanEngine) ForceReplacement(resourceType string, key string) bool {
	id := resourceType + "." + key
	if e.forces[id] {
		return false
	}
	e.forces[id] = true
	return true
}

func (e *PlanEngine) Computed(resourceType string, key string) bool {
	if e.computed[resourceType] == nil {
		e.computed[resourceType] = map[string]bool{}
	}
	if e.computed[resourceType][key] {
		return false
	}
	e.computed[resourceType][key] = true
	return true
}

func (e *PlanEngine) CreateBeforeDestroy(address string) bool {
	if e.marked[address] {
		return false
	}
	e.marked[address] = true
	return true
}

// Level 4

func (e *PlanEngine) Apply(failures [][]string, values [][]string) [][]string {
	errors, steps := e.build()
	if len(errors) > 0 {
		return errors
	}
	failing := map[string]bool{}
	for _, pair := range failures {
		failing[pair[0]+" "+pair[1]] = true
	}
	assigned := map[string]string{}
	for _, row := range values {
		assigned[row[0]+" "+row[1]] = row[2]
	}
	status := map[*step]string{}
	rows := [][]string{}
	for _, s := range steps {
		outcome := "ok"
		for _, prior := range s.before {
			if status[prior] != "ok" {
				outcome = "skipped"
			}
		}
		if outcome == "ok" && s.verb != "no-op" && failing[s.verb+" "+s.address] {
			outcome = "failed"
		}
		if outcome == "ok" {
			e.perform(s, assigned)
		}
		status[s] = outcome
		rows = append(rows, []string{s.verb, s.address, outcome})
	}
	return rows
}

func (e *PlanEngine) State() [][]string {
	seen := map[string]bool{}
	for address := range e.current {
		seen[address] = true
	}
	for address := range e.old {
		seen[address] = true
	}
	rows := [][]string{}
	for _, address := range sortedSet(seen) {
		for _, role := range []string{"current", "old"} {
			objects := e.current
			if role == "old" {
				objects = e.old
			}
			attributes, ok := objects[address]
			if !ok {
				continue
			}
			row := []string{address, role}
			for _, key := range sortedKeys(attributes) {
				row = append(row, key, attributes[key])
			}
			rows = append(rows, row)
		}
	}
	return rows
}

// Planning

func toMap(attributes [][]string) map[string]string {
	m := map[string]string{}
	for _, pair := range attributes {
		m[pair[0]] = pair[1]
	}
	return m
}

func sortedKeys(m map[string]string) []string {
	keys := make([]string, 0, len(m))
	for key := range m {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func sortedSet(m map[string]bool) []string {
	keys := make([]string, 0, len(m))
	for key := range m {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func sortByKey(rows [][]string) {
	sort.SliceStable(rows, func(i, j int) bool { return rows[i][1] < rows[j][1] })
}

// reference returns the target address and key of a ${type.name.key} value.
func reference(value string) (string, string, bool) {
	if !strings.HasPrefix(value, "${") || !strings.HasSuffix(value, "}") {
		return "", "", false
	}
	parts := strings.Split(value[2:len(value)-1], ".")
	return parts[0] + "." + parts[1], parts[2], true
}

func kindOf(address string) string {
	return address[:strings.IndexByte(address, '.')]
}

func (e *PlanEngine) isComputed(address, key string) bool {
	return e.computed[kindOf(address)][key]
}

func (e *PlanEngine) computedOf(address string) []string {
	return sortedSet(e.computed[kindOf(address)])
}

func removed(attributes map[string]string) [][]string {
	rows := [][]string{}
	for _, key := range sortedKeys(attributes) {
		rows = append(rows, []string{"-", key, attributes[key]})
	}
	return rows
}

func cycles(needs map[string]map[string]bool) [][]string {
	reach := map[string]map[string]bool{}
	for start, targets := range needs {
		seen := map[string]bool{}
		stack := sortedSet(targets)
		for len(stack) > 0 {
			node := stack[len(stack)-1]
			stack = stack[:len(stack)-1]
			if !seen[node] {
				seen[node] = true
				stack = append(stack, sortedSet(needs[node])...)
			}
		}
		reach[start] = seen
	}
	groups := map[string][]string{}
	for node := range needs {
		if reach[node][node] {
			group := []string{}
			for other := range reach[node] {
				if reach[other][node] {
					group = append(group, other)
				}
			}
			sort.Strings(group)
			groups[group[0]] = group
		}
	}
	firsts := make([]string, 0, len(groups))
	for first := range groups {
		firsts = append(firsts, first)
	}
	sort.Strings(firsts)
	rows := [][]string{}
	for _, first := range firsts {
		rows = append(rows, append([]string{"error", "cycle"}, groups[first]...))
	}
	return rows
}

func dependencyOrder(needs map[string]map[string]bool) []string {
	waiting := map[string]int{}
	users := map[string][]string{}
	for address, targets := range needs {
		waiting[address] = len(targets)
		for target := range targets {
			users[target] = append(users[target], address)
		}
	}
	ready := []string{}
	for address, count := range waiting {
		if count == 0 {
			ready = append(ready, address)
		}
	}
	order := []string{}
	for len(ready) > 0 {
		sort.Strings(ready)
		address := ready[0]
		ready = ready[1:]
		order = append(order, address)
		for _, user := range users[address] {
			waiting[user]--
			if waiting[user] == 0 {
				ready = append(ready, user)
			}
		}
	}
	return order
}

func (e *PlanEngine) createFirst(needs map[string]map[string]bool) map[string]bool {
	found := map[string]bool{}
	stack := []string{}
	for address := range e.marked {
		if _, ok := e.desired[address]; ok {
			stack = append(stack, address)
		}
	}
	for len(stack) > 0 {
		address := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if !found[address] {
			found[address] = true
			stack = append(stack, sortedSet(needs[address])...)
		}
	}
	return found
}

func link(first, second *step) {
	first.after = append(first.after, second)
	second.before = append(second.before, first)
}

func (e *PlanEngine) build() ([][]string, []*step) {
	errors := [][]string{}
	needs := map[string]map[string]bool{}
	desiredSet := map[string]bool{}
	for address := range e.desired {
		needs[address] = map[string]bool{}
		desiredSet[address] = true
	}
	for _, address := range sortedSet(desiredSet) {
		attributes := e.desired[address]
		for _, key := range sortedKeys(attributes) {
			other, wanted, ok := reference(attributes[key])
			if !ok {
				continue
			}
			declared, isDesired := e.desired[other]
			_, has := declared[wanted]
			if isDesired && (has || e.isComputed(other, wanted)) {
				needs[address][other] = true
			} else {
				errors = append(errors, []string{"error", "unknown-reference", address, key, other + "." + wanted})
			}
		}
	}
	errors = append(errors, cycles(needs)...)
	if len(errors) > 0 {
		return errors, nil
	}

	early := e.createFirst(needs)
	action := map[string]string{}
	resolved := map[string]map[string]string{}
	applies := map[string]*step{}
	deletes := map[string]*step{}
	for _, address := range dependencyOrder(needs) {
		values := map[string]string{}
		for key, value := range e.desired[address] {
			other, wanted, ok := reference(value)
			switch {
			case !ok:
				values[key] = value
			case e.isComputed(other, wanted):
				if action[other] == "create" || action[other] == "replace" {
					values[key] = unknown
				} else {
					values[key] = e.current[other][wanted]
				}
			default:
				values[key] = resolved[other][wanted]
			}
		}
		resolved[address] = values
		s := e.classify(address, values)
		kind := s.verb
		if s.verb == "create" && s.tag == "replace" {
			kind = "replace"
		}
		action[address] = kind
		applies[address] = s
		if kind == "replace" {
			half := &step{verb: "delete", address: address, tag: "replace", rank: 1, mode: deleteFirst}
			if early[address] {
				half.mode = createFirst
			}
			deletes[address] = half
		}
	}
	for address, attributes := range e.current {
		if _, ok := e.desired[address]; !ok {
			deletes[address] = &step{verb: "delete", address: address, rank: 1, diff: removed(attributes)}
		}
	}
	for address, attributes := range e.old {
		deletes[address] = &step{verb: "delete", address: address, tag: "old", rank: 1, diff: removed(attributes)}
	}

	for address, targets := range needs {
		for target := range targets {
			link(applies[target], applies[address])
		}
	}
	for address, s := range deletes {
		held := e.deps
		if s.tag == "old" {
			held = e.oldDeps
		}
		for target := range held[address] {
			if gone, ok := deletes[target]; ok {
				link(s, gone)
			}
		}
	}
	for address, s := range applies {
		if _, ok := e.current[address]; !ok {
			continue
		}
		for target := range e.deps[address] {
			if gone, ok := deletes[target]; ok && gone.mode != deleteFirst {
				link(s, gone)
			}
		}
	}
	for address, s := range deletes {
		if s.mode == deleteFirst {
			link(s, applies[address])
		} else if s.mode == createFirst {
			link(applies[address], s)
		}
	}
	all := []*step{}
	for _, s := range applies {
		all = append(all, s)
	}
	for _, s := range deletes {
		all = append(all, s)
	}
	return nil, order(all)
}

func (e *PlanEngine) classify(address string, values map[string]string) *step {
	computed := e.computedOf(address)
	existing, ok := e.current[address]
	if !ok {
		s := &step{verb: "create", address: address}
		for key, value := range values {
			s.diff = append(s.diff, []string{"+", key, value})
		}
		for _, name := range computed {
			s.diff = append(s.diff, []string{"+", name, unknown})
		}
		sortByKey(s.diff)
		return s
	}
	actual := map[string]string{}
	keys := map[string]bool{}
	for key, value := range existing {
		if !e.isComputed(address, key) {
			actual[key] = value
			keys[key] = true
		}
	}
	for key := range values {
		keys[key] = true
	}
	rows := [][]string{}
	forced := false
	for _, key := range sortedSet(keys) {
		before, hasBefore := actual[key]
		after, hasAfter := values[key]
		if hasBefore == hasAfter && before == after {
			continue
		}
		var row []string
		switch {
		case !hasBefore:
			row = []string{"+", key, after}
		case !hasAfter:
			row = []string{"-", key, before}
		default:
			row = []string{"~", key, before, after}
		}
		if e.forces[kindOf(address)+"."+key] {
			row = append(row, forcesMark)
			forced = true
		}
		rows = append(rows, row)
	}
	if len(rows) == 0 {
		return &step{verb: "no-op", address: address}
	}
	if !forced {
		return &step{verb: "update", address: address, diff: rows}
	}
	for _, name := range computed {
		if was, ok := existing[name]; ok {
			rows = append(rows, []string{"~", name, was, unknown})
		} else {
			rows = append(rows, []string{"+", name, unknown})
		}
	}
	sortByKey(rows)
	return &step{verb: "create", address: address, tag: "replace", diff: rows}
}

// order is Kahn's algorithm, always taking the smallest ready step by rank, then address.
func order(steps []*step) []*step {
	ready := &readySteps{}
	for _, s := range steps {
		s.waiting = len(s.before)
		if s.waiting == 0 {
			heap.Push(ready, s)
		}
	}
	result := []*step{}
	for ready.Len() > 0 {
		s := heap.Pop(ready).(*step)
		result = append(result, s)
		for _, later := range s.after {
			later.waiting--
			if later.waiting == 0 {
				heap.Push(ready, later)
			}
		}
	}
	return result
}

// Applying

func (e *PlanEngine) live(address, key string) string {
	value := e.desired[address][key]
	other, wanted, ok := reference(value)
	if !ok {
		return value
	}
	if e.isComputed(other, wanted) {
		return e.current[other][wanted]
	}
	return e.live(other, wanted)
}

func (e *PlanEngine) resolvedNow(address string) map[string]string {
	made := map[string]string{}
	for key := range e.desired[address] {
		made[key] = e.live(address, key)
	}
	return made
}

func (e *PlanEngine) perform(s *step, assigned map[string]string) {
	address := s.address
	needs := map[string]bool{}
	for _, value := range e.desired[address] {
		if other, _, ok := reference(value); ok {
			needs[other] = true
		}
	}
	switch s.verb {
	case "create":
		if existing, ok := e.current[address]; ok && s.tag == "replace" {
			e.old[address] = existing
			e.oldDeps[address] = e.deps[address]
		}
		made := e.resolvedNow(address)
		for _, name := range e.computedOf(address) {
			made[name] = assigned[address+" "+name]
		}
		e.current[address] = made
		e.deps[address] = needs
	case "update":
		made := e.resolvedNow(address)
		for key, value := range e.current[address] {
			if e.isComputed(address, key) {
				made[key] = value
			}
		}
		e.current[address] = made
		e.deps[address] = needs
	case "delete":
		if s.tag == "old" || s.mode == createFirst {
			delete(e.old, address)
			delete(e.oldDeps, address)
		} else {
			delete(e.current, address)
			delete(e.deps, address)
		}
	}
}
