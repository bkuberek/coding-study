package test_doubles

import (
	"container/heap"
	"sort"
	"strconv"
	"strings"
)

const (
	unknown    = "!unknown"
	unexpected = "!unexpected"
)

func fits(pattern []string, args []string) bool {
	if len(pattern) != len(args) {
		return false
	}
	for i, p := range pattern {
		if p != "*" && p != args[i] {
			return false
		}
	}
	return true
}

type rule struct {
	pattern []string
	answers []string
	used    int
}

func (r *rule) nextAnswer() string {
	index := r.used
	if index > len(r.answers)-1 {
		index = len(r.answers) - 1
	}
	r.used++
	return r.answers[index]
}

type expectation struct {
	method  string
	pattern []string
	answer  string
	times   int
	used    int
}

type surprise struct {
	method string
	args   []string
}

type double struct {
	mock         bool
	strict       bool
	rules        map[string][]*rule
	fallback     map[string]string
	expectations []*expectation
	unexpected   []surprise
	calls        []int
}

func (d *double) answer(method string, args []string) string {
	for _, e := range d.expectations {
		if e.method == method && e.used < e.times && fits(e.pattern, args) {
			e.used++
			return e.answer
		}
	}
	rules := d.rules[method]
	for i := len(rules) - 1; i >= 0; i-- {
		if fits(rules[i].pattern, args) {
			return rules[i].nextAnswer()
		}
	}
	if answer, ok := d.fallback[method]; ok {
		return answer
	}
	if !d.mock {
		return ""
	}
	d.unexpected = append(d.unexpected, surprise{method, args})
	if d.strict {
		return unexpected
	}
	return ""
}

type loggedCall struct {
	name   string
	method string
	args   []string
	time   int64
}

type timer struct {
	name     string
	method   string
	args     []string
	interval int64
	stopped  bool
}

type entry struct {
	due      int64
	sequence int64
	timerID  int
}

func before(a, b entry) bool {
	if a.due != b.due {
		return a.due < b.due
	}
	return a.sequence < b.sequence
}

type timerHeap []entry

func (h timerHeap) Len() int           { return len(h) }
func (h timerHeap) Less(i, j int) bool { return before(h[i], h[j]) }
func (h timerHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }
func (h *timerHeap) Push(x any)        { *h = append(*h, x.(entry)) }
func (h *timerHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

func copyOf(values []string) []string {
	return append([]string{}, values...)
}

// Doubles keeps, for every double, its stub rules per method, newest last, and for a mock its
// expectations in the order they were set. One log holds every call in the order it was made,
// with its time, and each double keeps the positions of its own calls in that log, so the spy
// questions read short lists. A slice of names keeps the order the doubles were made in.
// Timers wait in a heap ordered by due time, then by the sequence number they got when they
// were last put in, so equal times fire in scheduling order.
type Doubles struct {
	doubles  map[string]*double
	order    []string
	log      []loggedCall
	clock    int64
	timers   []*timer
	heap     timerHeap
	sequence int64
}

func NewDoubles() *Doubles {
	return &Doubles{doubles: map[string]*double{}}
}

// Level 1
func (d *Doubles) AddStub(name string) bool {
	return d.add(name, false, false)
}

func (d *Doubles) OnCall(name string, method string, args []string, answers []string) bool {
	target, ok := d.doubles[name]
	if !ok {
		return false
	}
	target.rules[method] = append(target.rules[method], &rule{pattern: copyOf(args), answers: copyOf(answers)})
	return true
}

func (d *Doubles) Otherwise(name string, method string, answer string) bool {
	target, ok := d.doubles[name]
	if !ok {
		return false
	}
	target.fallback[method] = answer
	return true
}

func (d *Doubles) Call(name string, method string, args []string) string {
	target, ok := d.doubles[name]
	if !ok {
		return unknown
	}
	copied := copyOf(args)
	target.calls = append(target.calls, len(d.log))
	d.log = append(d.log, loggedCall{name, method, copied, d.clock})
	return target.answer(method, copied)
}

// Level 2
func (d *Doubles) CallCount(name string, method string) int {
	return d.count(name, method, nil, false)
}

func (d *Doubles) MatchCount(name string, method string, args []string) int {
	return d.count(name, method, args, true)
}

func (d *Doubles) NthCall(name string, n int) []string {
	target, ok := d.doubles[name]
	if !ok || n == 0 || n > len(target.calls) || -n > len(target.calls) {
		return []string{}
	}
	position := n - 1
	if n < 0 {
		position = len(target.calls) + n
	}
	call := d.log[target.calls[position]]
	return append([]string{call.method}, call.args...)
}

func (d *Doubles) InOrder(steps [][]string) bool {
	step := 0
	for _, call := range d.log {
		if step == len(steps) {
			break
		}
		wanted := steps[step]
		if wanted[0] == call.name && wanted[1] == call.method && fits(wanted[2:], call.args) {
			step++
		}
	}
	return step == len(steps)
}

// Level 3
func (d *Doubles) AddMock(name string, strict bool) bool {
	return d.add(name, true, strict)
}

func (d *Doubles) Expect(name string, method string, args []string, answer string, times int) bool {
	target, ok := d.doubles[name]
	if !ok || !target.mock {
		return false
	}
	target.expectations = append(target.expectations,
		&expectation{method: method, pattern: copyOf(args), answer: answer, times: times})
	return true
}

func (d *Doubles) Verify(name string) []string {
	target, ok := d.doubles[name]
	if !ok {
		return []string{unknown}
	}
	report := []string{}
	for _, e := range target.expectations {
		if e.used < e.times {
			report = append(report, "missing "+name+"."+e.method+"("+strings.Join(e.pattern, ",")+") "+
				strconv.Itoa(e.used)+"/"+strconv.Itoa(e.times))
		}
	}
	for _, s := range target.unexpected {
		report = append(report, "unexpected "+name+"."+s.method+"("+strings.Join(s.args, ",")+")")
	}
	return report
}

func (d *Doubles) VerifyAll() []string {
	report := []string{}
	for _, name := range d.order {
		if d.doubles[name].mock {
			report = append(report, d.Verify(name)...)
		}
	}
	return report
}

// Level 4
func (d *Doubles) Now() int64 {
	return d.clock
}

func (d *Doubles) Schedule(delay int64, name string, method string, args []string) int {
	return d.timer(delay, 0, name, method, args)
}

func (d *Doubles) Every(interval int64, name string, method string, args []string) int {
	return d.timer(interval, interval, name, method, args)
}

func (d *Doubles) Cancel(timerId int) bool {
	if timerId < 1 || timerId > len(d.timers) || d.timers[timerId-1].stopped {
		return false
	}
	d.timers[timerId-1].stopped = true
	return true
}

func (d *Doubles) Advance(ms int64) []string {
	end := d.clock + ms
	fired := []string{}
	for d.heap.Len() > 0 && d.heap[0].due <= end {
		top := heap.Pop(&d.heap).(entry)
		t := d.timers[top.timerID-1]
		if t.stopped {
			continue
		}
		d.clock = top.due
		if t.interval > 0 {
			d.push(top.due+t.interval, top.timerID)
		} else {
			t.stopped = true
		}
		fired = append(fired, strconv.Itoa(top.timerID)+"@"+strconv.FormatInt(top.due, 10))
		d.Call(t.name, t.method, t.args)
	}
	d.clock = end
	return fired
}

func (d *Doubles) Pending() []string {
	live := []entry{}
	for _, e := range d.heap {
		if !d.timers[e.timerID-1].stopped {
			live = append(live, e)
		}
	}
	sort.Slice(live, func(i, j int) bool { return before(live[i], live[j]) })
	result := []string{}
	for _, e := range live {
		result = append(result, strconv.Itoa(e.timerID)+"@"+strconv.FormatInt(e.due, 10))
	}
	return result
}

func (d *Doubles) CallTimes(name string, method string) []int64 {
	times := []int64{}
	target, ok := d.doubles[name]
	if !ok {
		return times
	}
	for _, position := range target.calls {
		if d.log[position].method == method {
			times = append(times, d.log[position].time)
		}
	}
	return times
}

func (d *Doubles) count(name string, method string, pattern []string, usePattern bool) int {
	target, ok := d.doubles[name]
	if !ok {
		return -1
	}
	total := 0
	for _, position := range target.calls {
		call := d.log[position]
		if call.method == method && (!usePattern || fits(pattern, call.args)) {
			total++
		}
	}
	return total
}

func (d *Doubles) add(name string, mock bool, strict bool) bool {
	if _, taken := d.doubles[name]; taken {
		return false
	}
	d.doubles[name] = &double{
		mock:     mock,
		strict:   strict,
		rules:    map[string][]*rule{},
		fallback: map[string]string{},
	}
	d.order = append(d.order, name)
	return true
}

func (d *Doubles) timer(delay int64, interval int64, name string, method string, args []string) int {
	if _, ok := d.doubles[name]; !ok {
		return -1
	}
	d.timers = append(d.timers, &timer{name: name, method: method, args: copyOf(args), interval: interval})
	d.push(d.clock+delay, len(d.timers))
	return len(d.timers)
}

func (d *Doubles) push(due int64, timerID int) {
	d.sequence++
	heap.Push(&d.heap, entry{due, d.sequence, timerID})
}
