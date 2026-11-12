package property_test_runner

import (
	"sort"
	"strconv"
	"strings"
)

type genKind int

const (
	intGen genKind = iota
	listGen
	pairGen
	filterGen
)

type recipe struct {
	kind     genKind
	low      int
	high     int
	name     string
	children []*recipe
}

type valueKind int

const (
	intValue valueKind = iota
	listValue
	pairValue
)

// value is an integer, a list (items) or a pair (items[0] and items[1]).
type value struct {
	kind   valueKind
	number int
	items  []value
}

type randomStream struct {
	state    uint32
	discards int
	limit    int
}

func (r *randomStream) next() uint32 {
	x := r.state
	x ^= x << 13
	x ^= x >> 17
	x ^= x << 5
	r.state = x
	return x
}

func (r *randomStream) between(low int, high int) int {
	return low + int(int64(r.next())%int64(high-low+1))
}

// discard counts one discarded value and reports whether the call may go on.
func (r *randomStream) discard() bool {
	r.discards++
	return r.discards <= r.limit
}

func parse(tokens []string, at int) (*recipe, int) {
	number := func(i int) int {
		n, _ := strconv.Atoi(tokens[i])
		return n
	}
	switch tokens[at] {
	case "int":
		return &recipe{kind: intGen, low: number(at + 1), high: number(at + 2)}, at + 3
	case "list":
		element, end := parse(tokens, at+3)
		return &recipe{kind: listGen, low: number(at + 1), high: number(at + 2), children: []*recipe{element}}, end
	case "pair":
		first, middle := parse(tokens, at+1)
		second, end := parse(tokens, middle)
		return &recipe{kind: pairGen, children: []*recipe{first, second}}, end
	}
	inner, end := parse(tokens, at+2)
	return &recipe{kind: filterGen, name: tokens[at+1], children: []*recipe{inner}}, end
}

func generator(text string) *recipe {
	parsed, _ := parse(strings.Split(text, " "), 0)
	return parsed
}

// draw makes one value; ok is false when the call has discarded more values than its limit.
func draw(g *recipe, rng *randomStream) (value, bool) {
	switch g.kind {
	case intGen:
		return value{kind: intValue, number: rng.between(g.low, g.high)}, true
	case listGen:
		length := rng.between(g.low, g.high)
		items := make([]value, 0, length)
		for i := 0; i < length; i++ {
			item, ok := draw(g.children[0], rng)
			if !ok {
				return value{}, false
			}
			items = append(items, item)
		}
		return value{kind: listValue, items: items}, true
	case pairGen:
		first, ok := draw(g.children[0], rng)
		if !ok {
			return value{}, false
		}
		second, ok := draw(g.children[1], rng)
		if !ok {
			return value{}, false
		}
		return value{kind: pairValue, items: []value{first, second}}, true
	}
	for {
		v, ok := draw(g.children[0], rng)
		if !ok {
			return value{}, false
		}
		if passesFilter(g.name, v) {
			return v, true
		}
		if !rng.discard() {
			return value{}, false
		}
	}
}

func text(v value) string {
	switch v.kind {
	case intValue:
		return strconv.Itoa(v.number)
	case listValue:
		parts := make([]string, len(v.items))
		for i, item := range v.items {
			parts[i] = text(item)
		}
		return "[" + strings.Join(parts, ",") + "]"
	}
	return "(" + text(v.items[0]) + "," + text(v.items[1]) + ")"
}

func passesFilter(name string, v value) bool {
	switch name {
	case "even":
		return v.number%2 == 0
	case "odd":
		return v.number%2 != 0
	case "nonzero":
		return v.number != 0
	case "positive":
		return v.number > 0
	case "nonempty":
		return len(v.items) > 0
	case "distinct":
		seen := map[string]bool{}
		for _, item := range v.items {
			seen[text(item)] = true
		}
		return len(seen) == len(v.items)
	}
	return text(v.items[0]) != text(v.items[1])
}

func total(v value) int {
	if v.kind == intValue {
		return v.number
	}
	sum := 0
	for _, item := range v.items {
		sum += total(item)
	}
	return sum
}

func numbers(v value) []int {
	result := make([]int, len(v.items))
	for i, item := range v.items {
		result[i] = item.number
	}
	return result
}

func ordered(values []int) bool {
	for i := 0; i+1 < len(values); i++ {
		if values[i] > values[i+1] {
			return false
		}
	}
	return true
}

func holds(prop string, v value) bool {
	parts := strings.Split(prop, " ")
	k := 0
	if len(parts) > 1 {
		k, _ = strconv.Atoi(parts[1])
	}
	switch parts[0] {
	case "lt":
		return v.number < k
	case "not-multiple":
		return v.number%k != 0
	case "sum-lt":
		return total(v) < k
	case "len-lt":
		return len(v.items) < k
	case "ordered":
		return ordered(numbers(v))
	case "sort-ordered":
		list := numbers(v)
		sort.Ints(list)
		return ordered(list)
	case "one-pass-ordered":
		list := numbers(v)
		for i := 0; i+1 < len(list); i++ {
			if list[i] > list[i+1] {
				list[i], list[i+1] = list[i+1], list[i]
			}
		}
		return ordered(list)
	case "max-from-zero":
		list := numbers(v)
		if len(list) == 0 {
			return true
		}
		best, largest := 0, list[0]
		for _, item := range list {
			best = max(best, item)
			largest = max(largest, item)
		}
		return best == largest
	case "keys-distinct":
		keys := map[string]bool{}
		for _, pair := range v.items {
			keys[text(pair.items[0])] = true
		}
		return len(keys) == len(v.items)
	}
	first := map[string]string{}
	last := map[string]string{}
	for _, pair := range v.items {
		key := text(pair.items[0])
		if _, seen := first[key]; !seen {
			first[key] = text(pair.items[1])
		}
		last[key] = text(pair.items[1])
	}
	for key, item := range first {
		if last[key] != item {
			return false
		}
	}
	return true
}

func intCandidates(low int, high int, x int) []int {
	target := 0
	if low > 0 {
		target = low
	} else if high < 0 {
		target = high
	}
	if x == target {
		return nil
	}
	found := []int{target}
	for step := (x - target) / 2; step != 0; step /= 2 {
		found = append(found, x-step)
	}
	return found
}

func removals[T any](items []T, shortest int) [][]T {
	n := len(items)
	var found [][]T
	for size := n; size >= 1; size /= 2 {
		if n-size < shortest {
			continue
		}
		for start := 0; start+size <= n; start += size {
			shorter := append(append([]T{}, items[:start]...), items[start+size:]...)
			found = append(found, shorter)
		}
	}
	return found
}

func replaced[T any](items []T, index int, item T) []T {
	copied := append([]T{}, items...)
	copied[index] = item
	return copied
}

func withoutRepeats[T any](v T, found []T, show func(T) string) []T {
	seen := map[string]bool{show(v): true}
	kept := []T{}
	for _, candidate := range found {
		key := show(candidate)
		if !seen[key] {
			seen[key] = true
			kept = append(kept, candidate)
		}
	}
	return kept
}

func candidatesOf(g *recipe, v value) []value {
	var found []value
	switch g.kind {
	case intGen:
		for _, smaller := range intCandidates(g.low, g.high, v.number) {
			found = append(found, value{kind: intValue, number: smaller})
		}
	case listGen:
		for _, shorter := range removals(v.items, g.low) {
			found = append(found, value{kind: listValue, items: shorter})
		}
		for i, item := range v.items {
			for _, smaller := range candidatesOf(g.children[0], item) {
				found = append(found, value{kind: listValue, items: replaced(v.items, i, smaller)})
			}
		}
	case pairGen:
		for _, smaller := range candidatesOf(g.children[0], v.items[0]) {
			found = append(found, value{kind: pairValue, items: []value{smaller, v.items[1]}})
		}
		for _, smaller := range candidatesOf(g.children[1], v.items[1]) {
			found = append(found, value{kind: pairValue, items: []value{v.items[0], smaller}})
		}
	case filterGen:
		for _, candidate := range candidatesOf(g.children[0], v) {
			if passesFilter(g.name, candidate) {
				found = append(found, candidate)
			}
		}
	}
	return withoutRepeats(v, found, text)
}

type boundedQueue struct {
	capacity int
	bug      string
	items    []int
	puts     int
}

func (q *boundedQueue) allows(command string) bool {
	return command != "get" || len(q.items) > 0
}

func (q *boundedQueue) apply(command string) string {
	if command == "size" {
		count := len(q.items)
		if q.bug == "size-wraps" {
			count %= q.capacity
		}
		return strconv.Itoa(count)
	}
	if command == "get" {
		if len(q.items) == 0 {
			return "empty"
		}
		if q.bug == "wrap-lifo" && q.puts > q.capacity {
			back := q.items[len(q.items)-1]
			q.items = q.items[:len(q.items)-1]
			return strconv.Itoa(back)
		}
		front := q.items[0]
		q.items = q.items[1:]
		return strconv.Itoa(front)
	}
	v, _ := strconv.Atoi(command[4:])
	if len(q.items) == q.capacity {
		if q.bug != "full-overwrites" {
			return "full"
		}
		q.items = q.items[1:]
	} else if q.bug == "repeat-dropped" && len(q.items) > 0 && q.items[len(q.items)-1] == v {
		q.puts++
		return "ok"
	}
	q.items = append(q.items, v)
	q.puts++
	return "ok"
}

func valid(capacity int, commands []string) bool {
	model := &boundedQueue{capacity: capacity, bug: "none"}
	for _, command := range commands {
		if !model.allows(command) {
			return false
		}
		model.apply(command)
	}
	return true
}

func fails(capacity int, bug string, commands []string) bool {
	model := &boundedQueue{capacity: capacity, bug: "none"}
	system := &boundedQueue{capacity: capacity, bug: bug}
	for _, command := range commands {
		if model.apply(command) != system.apply(command) {
			return true
		}
	}
	return false
}

func sequence(capacity int, rng *randomStream, longest int) []string {
	model := &boundedQueue{capacity: capacity, bug: "none"}
	length := rng.between(1, longest)
	commands := make([]string, 0, length)
	for i := 0; i < length; i++ {
		allowed := []string{"put", "size"}
		if len(model.items) > 0 {
			allowed = []string{"put", "get", "size"}
		}
		command := allowed[rng.next()%uint32(len(allowed))]
		if command == "put" {
			command = "put " + strconv.Itoa(rng.between(0, 9))
		}
		model.apply(command)
		commands = append(commands, command)
	}
	return commands
}

func sequenceCandidates(capacity int, commands []string) [][]string {
	found := removals(commands, 1)
	for i, command := range commands {
		if strings.HasPrefix(command, "put ") {
			v, _ := strconv.Atoi(command[4:])
			for _, smaller := range intCandidates(0, 9, v) {
				found = append(found, replaced(commands, i, "put "+strconv.Itoa(smaller)))
			}
		}
	}
	kept := [][]string{}
	join := func(c []string) string { return strings.Join(c, ", ") }
	for _, candidate := range withoutRepeats(commands, found, join) {
		if valid(capacity, candidate) {
			kept = append(kept, candidate)
		}
	}
	return kept
}

// PropertyRunner parses generators from prefix token lists into a small tree. One xorshift32
// stream feeds a whole call, so every value is fixed by the seed and its position. Shrinking is
// greedy: from the failing value, take the first candidate that still fails, and start again
// from it, until no candidate fails. Candidates are built from the generator, so each one is a
// value the generator could have drawn: in range, long enough and through every filter. The
// stateful level runs each command sequence on the correct queue and on the buggy one and
// shrinks the sequence the same way, keeping only sequences whose commands are all allowed.
type PropertyRunner struct {
	limit int
}

func NewPropertyRunner() *PropertyRunner {
	return &PropertyRunner{limit: 100}
}

func (p *PropertyRunner) stream(seed int) *randomStream {
	return &randomStream{state: uint32(seed), limit: p.limit}
}

// Level 1
func (p *PropertyRunner) Randoms(seed int, count int) []int64 {
	rng := p.stream(seed)
	numbers := make([]int64, count)
	for i := range numbers {
		numbers[i] = int64(rng.next())
	}
	return numbers
}

func (p *PropertyRunner) Generate(gen string, seed int, count int) []string {
	rng := p.stream(seed)
	parsed := generator(gen)
	values := []string{}
	for i := 0; i < count; i++ {
		v, ok := draw(parsed, rng)
		if !ok {
			break
		}
		values = append(values, text(v))
	}
	return values
}

func (p *PropertyRunner) Check(gen string, prop string, seed int, runs int) string {
	outcome, run, v := p.search(gen, prop, seed, runs)
	switch outcome {
	case "failed":
		return "failed " + strconv.Itoa(run) + ": " + text(v)
	case "gave up":
		return "gave up after " + strconv.Itoa(run)
	}
	return "passed " + strconv.Itoa(runs)
}

// Level 2
func (p *PropertyRunner) Candidates(gen string, seed int, index int) []string {
	rng := p.stream(seed)
	parsed := generator(gen)
	var v value
	for i := 0; i < index; i++ {
		drawn, ok := draw(parsed, rng)
		if !ok {
			return []string{}
		}
		v = drawn
	}
	result := []string{}
	for _, candidate := range candidatesOf(parsed, v) {
		result = append(result, text(candidate))
	}
	return result
}

func (p *PropertyRunner) Minimize(gen string, prop string, seed int, runs int) []string {
	outcome, _, v := p.search(gen, prop, seed, runs)
	if outcome != "failed" {
		return []string{}
	}
	parsed := generator(gen)
	path := []string{text(v)}
	for {
		moved := false
		for _, candidate := range candidatesOf(parsed, v) {
			if !holds(prop, candidate) {
				v = candidate
				moved = true
				break
			}
		}
		if !moved {
			return path
		}
		path = append(path, text(v))
	}
}

// Level 3
func (p *PropertyRunner) SetDiscardLimit(limit int) {
	p.limit = limit
}

// Level 4
func (p *PropertyRunner) Replay(capacity int, bug string, commands []string) []string {
	model := &boundedQueue{capacity: capacity, bug: "none"}
	system := &boundedQueue{capacity: capacity, bug: bug}
	answers := []string{}
	for _, command := range commands {
		if !model.allows(command) {
			answers = append(answers, "invalid")
			break
		}
		model.apply(command)
		answers = append(answers, system.apply(command))
	}
	return answers
}

func (p *PropertyRunner) GenerateCommands(capacity int, seed int, count int, maxLength int) []string {
	rng := p.stream(seed)
	sequences := make([]string, count)
	for i := range sequences {
		sequences[i] = strings.Join(sequence(capacity, rng, maxLength), ", ")
	}
	return sequences
}

func (p *PropertyRunner) FirstFailure(capacity int, bug string, seed int, runs int, maxLength int) []string {
	rng := p.stream(seed)
	for i := 0; i < runs; i++ {
		commands := sequence(capacity, rng, maxLength)
		if fails(capacity, bug, commands) {
			return commands
		}
	}
	return []string{}
}

func (p *PropertyRunner) ShrinkFailure(capacity int, bug string, seed int, runs int, maxLength int) []string {
	commands := p.FirstFailure(capacity, bug, seed, runs, maxLength)
	for len(commands) > 0 {
		moved := false
		for _, candidate := range sequenceCandidates(capacity, commands) {
			if fails(capacity, bug, candidate) {
				commands = candidate
				moved = true
				break
			}
		}
		if !moved {
			break
		}
	}
	return commands
}

func (p *PropertyRunner) search(gen string, prop string, seed int, runs int) (string, int, value) {
	rng := p.stream(seed)
	parsed := generator(gen)
	for run := 1; run <= runs; run++ {
		v, ok := draw(parsed, rng)
		if !ok {
			return "gave up", run - 1, value{}
		}
		if !holds(prop, v) {
			return "failed", run, v
		}
	}
	return "passed", runs, value{}
}
