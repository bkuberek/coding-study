package pipeline_scheduler

import (
	"container/heap"
	"slices"
	"sort"
	"strconv"
)

const (
	done    = "done"
	failed  = "failed"
	missing = "missing"
)

type part struct {
	task string
	day  int
}

type edge struct{ task, dep string }

type outcome struct {
	round    int
	status   string
	attempts int
}

// names is a min-heap of task names for container/heap.
type names []string

func (h names) Len() int           { return len(h) }
func (h names) Less(i, j int) bool { return h[i] < h[j] }
func (h names) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }
func (h *names) Push(x any)        { *h = append(*h, x.(string)) }
func (h *names) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

// PipelineScheduler keeps tasks and their dependencies as a graph. The order counts the unlisted
// dependencies of each task and keeps the ready names in a heap, so that the smallest ready name
// goes next.
//
// A ledger keyed by (task, day) records each partition's state. Every write gets a number, and the
// partition remembers the number of each input it read, which is all it takes to tell a stale
// partition and to find what a backfill must rerun. Runs and backfills share one attempt loop,
// which follows the scripted outcomes and the task's retries.
type PipelineScheduler struct {
	tasks   []string
	deps    map[string][]string
	windows map[edge]int
	retries map[string]int
	scripts map[part][]string
	state   map[part]string
	written map[part]int
	reads   map[part]map[part]int
	writes  int
}

func NewPipelineScheduler() *PipelineScheduler {
	return &PipelineScheduler{
		deps:    map[string][]string{},
		windows: map[edge]int{},
		retries: map[string]int{},
		scripts: map[part][]string{},
		state:   map[part]string{},
		written: map[part]int{},
		reads:   map[part]map[part]int{},
	}
}

// Level 1
func (s *PipelineScheduler) AddTask(name string, deps []string) bool {
	if _, found := s.deps[name]; found {
		return false
	}
	unique := []string{}
	for _, dep := range deps {
		if !slices.Contains(unique, dep) {
			unique = append(unique, dep)
		}
	}
	s.tasks = append(s.tasks, name)
	s.deps[name] = unique
	return true
}

func (s *PipelineScheduler) Validate() [][]string {
	problems := [][]string{}
	for _, task := range s.tasks {
		for _, dep := range s.deps[task] {
			if _, found := s.deps[dep]; !found {
				problems = append(problems, []string{"unknown-dependency", task, dep})
			}
		}
	}
	listed := map[string]bool{}
	for _, task := range s.order() {
		listed[task] = true
	}
	for _, task := range s.tasks {
		if !listed[task] && s.reachesItself(task) {
			problems = append(problems, []string{"cycle", task})
		}
	}
	sort.Slice(problems, func(i, j int) bool { return slices.Compare(problems[i], problems[j]) < 0 })
	return problems
}

func (s *PipelineScheduler) RunOrder() []string {
	if len(s.Validate()) > 0 {
		return []string{}
	}
	return s.order()
}

// Level 2
func (s *PipelineScheduler) SetWindow(task string, dep string, days int) bool {
	if !slices.Contains(s.deps[task], dep) {
		return false
	}
	s.windows[edge{task, dep}] = days
	return true
}

func (s *PipelineScheduler) MarkDone(task string, day int) {
	s.store(task, day)
}

func (s *PipelineScheduler) Runnable(day int) []string {
	out := []string{}
	for _, task := range s.tasks {
		if s.state[part{task, day}] != done && s.inputsDone(task, day) {
			out = append(out, task)
		}
	}
	sort.Strings(out)
	return out
}

// Level 3
func (s *PipelineScheduler) SetRetries(task string, retries int) {
	s.retries[task] = retries
}

func (s *PipelineScheduler) Script(task string, day int, outcomes []string) {
	s.scripts[part{task, day}] = append([]string{}, outcomes...)
}

func (s *PipelineScheduler) Run(day int) [][]string {
	rows := [][]string{}
	for _, task := range s.RunOrder() {
		if !s.inputsDone(task, day) {
			rows = append(rows, []string{task, "skipped", "0"})
			continue
		}
		attempts, succeeded := s.attempt(task, day)
		rows = append(rows, []string{task, result(succeeded), strconv.Itoa(attempts)})
	}
	return rows
}

func (s *PipelineScheduler) Status(task string, day int) string {
	if st, found := s.state[part{task, day}]; found {
		return st
	}
	return missing
}

// Level 4
func (s *PipelineScheduler) Stale(day int) []string {
	out := []string{}
	for _, task := range s.tasks {
		if s.isStale(part{task, day}) {
			out = append(out, task)
		}
	}
	sort.Strings(out)
	return out
}

func (s *PipelineScheduler) Plan(task string, fromDay int, toDay int) [][]string {
	rows := [][]string{}
	for _, p := range s.makePlan(task, fromDay, toDay) {
		rows = append(rows, []string{strconv.Itoa(p.day), p.task})
	}
	return rows
}

func (s *PipelineScheduler) Backfill(task string, fromDay int, toDay int, cap int) [][]string {
	plan := s.makePlan(task, fromDay, toDay)
	planned := map[part]bool{}
	for _, p := range plan {
		planned[p] = true
	}
	results := map[part]outcome{}
	round := 0
	for len(results) < len(plan) {
		round++
		// Inputs come before their users in plan order, so one pass settles every skip.
		for _, p := range plan {
			if _, found := results[p]; !found && s.blocked(p, planned, results) {
				results[p] = outcome{round, "skipped", 0}
			}
		}
		var ready []part
		for _, p := range plan {
			if _, found := results[p]; !found && len(ready) < cap && s.plannedInputsSucceeded(p, planned, results) {
				ready = append(ready, p)
			}
		}
		for _, p := range ready {
			attempts, succeeded := s.attempt(p.task, p.day)
			results[p] = outcome{round, result(succeeded), attempts}
		}
	}
	rank := s.rank()
	decided := append([]part{}, plan...)
	sort.SliceStable(decided, func(i, j int) bool {
		a, b := decided[i], decided[j]
		if results[a].round != results[b].round {
			return results[a].round < results[b].round
		}
		if a.day != b.day {
			return a.day < b.day
		}
		return rank[a.task] < rank[b.task]
	})
	rows := [][]string{}
	for _, p := range decided {
		o := results[p]
		rows = append(rows, []string{strconv.Itoa(o.round), strconv.Itoa(p.day), p.task, o.status, strconv.Itoa(o.attempts)})
	}
	return rows
}

// The graph
func result(succeeded bool) string {
	if succeeded {
		return "success"
	}
	return "failed"
}

func (s *PipelineScheduler) users() map[string][]string {
	users := map[string][]string{}
	for _, task := range s.tasks {
		for _, dep := range s.deps[task] {
			if _, found := s.deps[dep]; found {
				users[dep] = append(users[dep], task)
			}
		}
	}
	return users
}

func (s *PipelineScheduler) order() []string {
	waiting := map[string]int{}
	ready := &names{}
	for _, task := range s.tasks {
		for _, dep := range s.deps[task] {
			if _, found := s.deps[dep]; found {
				waiting[task]++
			}
		}
		if waiting[task] == 0 {
			heap.Push(ready, task)
		}
	}
	users := s.users()
	order := []string{}
	for ready.Len() > 0 {
		task := heap.Pop(ready).(string)
		order = append(order, task)
		for _, user := range users[task] {
			waiting[user]--
			if waiting[user] == 0 {
				heap.Push(ready, user)
			}
		}
	}
	return order
}

func (s *PipelineScheduler) reachesItself(start string) bool {
	seen := map[string]bool{}
	stack := append([]string{}, s.deps[start]...)
	for len(stack) > 0 {
		task := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if _, found := s.deps[task]; !found {
			continue
		}
		if task == start {
			return true
		}
		if !seen[task] {
			seen[task] = true
			stack = append(stack, s.deps[task]...)
		}
	}
	return false
}

func (s *PipelineScheduler) rank() map[string]int {
	rank := map[string]int{}
	for i, task := range s.RunOrder() {
		rank[task] = i
	}
	return rank
}

// The partitions
func (s *PipelineScheduler) width(task, dep string) int {
	if w, found := s.windows[edge{task, dep}]; found {
		return w
	}
	return 1
}

func (s *PipelineScheduler) inputs(task string, day int) []part {
	var inputs []part
	for _, dep := range s.deps[task] {
		for d := max(0, day-s.width(task, dep)+1); d <= day; d++ {
			inputs = append(inputs, part{dep, d})
		}
	}
	return inputs
}

func (s *PipelineScheduler) current(p part) int {
	if s.state[p] == done {
		return s.written[p]
	}
	return 0
}

func (s *PipelineScheduler) inputsDone(task string, day int) bool {
	for _, p := range s.inputs(task, day) {
		if s.state[p] != done {
			return false
		}
	}
	return true
}

func (s *PipelineScheduler) store(task string, day int) {
	s.writes++
	p := part{task, day}
	s.state[p] = done
	s.written[p] = s.writes
	seen := map[part]int{}
	for _, input := range s.inputs(task, day) {
		seen[input] = s.current(input)
	}
	s.reads[p] = seen
}

func (s *PipelineScheduler) attempt(task string, day int) (int, bool) {
	p := part{task, day}
	limit := 1 + s.retries[task]
	for attempt := 1; attempt <= limit; attempt++ {
		next := "ok"
		if script := s.scripts[p]; len(script) > 0 {
			next = script[0]
			s.scripts[p] = script[1:]
		}
		if next == "ok" {
			s.store(task, day)
			return attempt, true
		}
	}
	s.state[p] = failed
	return limit, false
}

func (s *PipelineScheduler) isStale(p part) bool {
	if s.state[p] != done {
		return false
	}
	for input, seen := range s.reads[p] {
		if s.current(input) != seen {
			return true
		}
	}
	return false
}

func (s *PipelineScheduler) makePlan(task string, fromDay, toDay int) []part {
	users := s.users()
	planned := map[part]bool{}
	var frontier []part
	for day := fromDay; day <= toDay; day++ {
		planned[part{task, day}] = true
		frontier = append(frontier, part{task, day})
	}
	for len(frontier) > 0 {
		p := frontier[len(frontier)-1]
		frontier = frontier[:len(frontier)-1]
		for _, user := range users[p.task] {
			for later := p.day; later < p.day+s.width(user, p.task); later++ {
				next := part{user, later}
				if s.state[next] == done && !planned[next] {
					planned[next] = true
					frontier = append(frontier, next)
				}
			}
		}
	}
	rank := s.rank()
	plan := make([]part, 0, len(planned))
	for p := range planned {
		plan = append(plan, p)
	}
	sort.Slice(plan, func(i, j int) bool {
		if plan[i].day != plan[j].day {
			return plan[i].day < plan[j].day
		}
		return rank[plan[i].task] < rank[plan[j].task]
	})
	return plan
}

func (s *PipelineScheduler) blocked(p part, planned map[part]bool, results map[part]outcome) bool {
	for _, input := range s.inputs(p.task, p.day) {
		if planned[input] {
			if o, found := results[input]; found && o.status != "success" {
				return true
			}
		} else if s.state[input] != done {
			return true
		}
	}
	return false
}

func (s *PipelineScheduler) plannedInputsSucceeded(p part, planned map[part]bool, results map[part]outcome) bool {
	for _, input := range s.inputs(p.task, p.day) {
		if planned[input] {
			if o, found := results[input]; !found || o.status != "success" {
				return false
			}
		}
	}
	return true
}
