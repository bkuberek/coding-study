package idempotent_converge

import (
	"regexp"
	"sort"
	"strconv"
)

var (
	counted = []string{"ok", "changed", "failed", "skipped"}
	whole   = regexp.MustCompile(`^-?[0-9]+$`)
)

type host struct {
	files    map[string]string
	packages map[string]string
	facts    map[string]string
}

func newHost() *host {
	return &host{files: map[string]string{}, packages: map[string]string{}, facts: map[string]string{}}
}

func (h *host) clone() *host {
	c := &host{files: map[string]string{}, packages: map[string]string{}, facts: h.facts}
	for path, content := range h.files {
		c.files[path] = content
	}
	for name, service := range h.packages {
		c.packages[name] = service
	}
	return c
}

type action struct {
	name, kind, target, value string
}

// Converger keeps tasks that describe the state a host should be in. Running a task compares
// that state with the host's and changes the host only when they differ, so a second run finds
// nothing to do. A run works through the hosts in batches; in each batch it applies every task to
// every host still standing, then the handlers that a change notified. A check run does the same
// on copies of the hosts, so later tasks see what earlier ones would have done while the real
// hosts stay as they were.
type Converger struct {
	order      []string
	hosts      map[string]*host
	tasks      []action
	handlers   []action
	links      map[string][]string
	conditions map[string][]action
	batch      int
	counts     map[string]map[string]int
}

func NewConverger() *Converger {
	return &Converger{
		hosts:      map[string]*host{},
		links:      map[string][]string{},
		conditions: map[string][]action{},
		counts:     map[string]map[string]int{},
	}
}

// Level 1

func (c *Converger) AddHost(name string) bool {
	if _, ok := c.hosts[name]; ok {
		return false
	}
	c.hosts[name] = newHost()
	c.order = append(c.order, name)
	return true
}

func (c *Converger) SetState(name string, kind string, target string, value string) bool {
	h, ok := c.hosts[name]
	if !ok {
		return false
	}
	apply(h, kind, target, value)
	return true
}

func find(list []action, name string) bool {
	for _, a := range list {
		if a.name == name {
			return true
		}
	}
	return false
}

func (c *Converger) AddTask(name string, kind string, target string, value string) bool {
	if find(c.tasks, name) {
		return false
	}
	c.tasks = append(c.tasks, action{name, kind, target, value})
	return true
}

func (c *Converger) Run() [][]string {
	fresh := c.zeros()
	rows := c.play(c.hosts, false, fresh)
	c.counts = fresh
	return rows
}

func (c *Converger) State(name string) [][]string {
	rows := [][]string{}
	h, ok := c.hosts[name]
	if !ok {
		return rows
	}
	for path, content := range h.files {
		rows = append(rows, []string{"file", path, content})
	}
	for pkg, service := range h.packages {
		rows = append(rows, []string{"package", pkg, "present"}, []string{"service", pkg, service})
	}
	sort.Slice(rows, func(i, j int) bool {
		if rows[i][0] != rows[j][0] {
			return rows[i][0] < rows[j][0]
		}
		return rows[i][1] < rows[j][1]
	})
	return rows
}

// Level 2

func (c *Converger) Check() [][]string {
	copies := map[string]*host{}
	for name, h := range c.hosts {
		copies[name] = h.clone()
	}
	return c.play(copies, true, c.zeros())
}

// Level 3

func (c *Converger) AddHandler(name string, kind string, target string, value string) bool {
	if find(c.handlers, name) {
		return false
	}
	c.handlers = append(c.handlers, action{name, kind, target, value})
	return true
}

func (c *Converger) Notifies(task string, handler string) bool {
	if !find(c.tasks, task) || !find(c.handlers, handler) {
		return false
	}
	for _, linked := range c.links[task] {
		if linked == handler {
			return false
		}
	}
	c.links[task] = append(c.links[task], handler)
	return true
}

// Level 4

func (c *Converger) SetFact(name string, key string, value string) bool {
	h, ok := c.hosts[name]
	if !ok {
		return false
	}
	_, had := h.facts[key]
	h.facts[key] = value
	return !had
}

func (c *Converger) OnlyIf(task string, fact string, comparison string, value string) bool {
	if !find(c.tasks, task) {
		return false
	}
	c.conditions[task] = append(c.conditions[task], action{fact, comparison, value, ""})
	return true
}

func (c *Converger) SetBatchSize(size int) bool {
	changed := size != c.batch
	c.batch = size
	return changed
}

func (c *Converger) Summary() [][]string {
	rows := [][]string{}
	for _, name := range c.order {
		row := []string{name}
		for _, status := range counted {
			row = append(row, strconv.Itoa(c.counts[name][status]))
		}
		rows = append(rows, row)
	}
	return rows
}

// Running

func (c *Converger) zeros() map[string]map[string]int {
	fresh := map[string]map[string]int{}
	for _, name := range c.order {
		fresh[name] = map[string]int{}
	}
	return fresh
}

func (c *Converger) play(on map[string]*host, dry bool, tally map[string]map[string]int) [][]string {
	size := c.batch
	if size <= 0 {
		size = len(c.order)
		if size == 0 {
			size = 1
		}
	}
	rows := [][]string{}
	record := func(name, step, status string, diff []string) {
		tally[name][status]++
		row := []string{name, step, status}
		if dry {
			row = append(row, diff...)
		}
		rows = append(rows, row)
	}
	for start := 0; start < len(c.order); start += size {
		end := start + size
		if end > len(c.order) {
			end = len(c.order)
		}
		group := c.order[start:end]
		failed := map[string]bool{}
		notified := map[string]map[string]bool{}
		for _, name := range group {
			notified[name] = map[string]bool{}
		}
		for _, t := range c.tasks {
			for _, name := range group {
				if failed[name] {
					continue
				}
				status, diff := c.task(on[name], t)
				switch status {
				case "failed":
					failed[name] = true
				case "changed":
					for _, handler := range c.links[t.name] {
						notified[name][handler] = true
					}
				}
				record(name, t.name, status, diff)
			}
		}
		for _, hd := range c.handlers {
			for _, name := range group {
				if failed[name] || !notified[name][hd.name] {
					continue
				}
				status, diff := change(on[name], hd)
				if status == "failed" {
					failed[name] = true
				}
				record(name, hd.name, status, diff)
			}
		}
		if len(failed) == len(group) {
			break
		}
	}
	return rows
}

func (c *Converger) task(h *host, t action) (string, []string) {
	for _, cond := range c.conditions[t.name] {
		have, ok := h.facts[cond.name]
		if !ok {
			return "failed", nil
		}
		holds, decided := compare(have, cond.kind, cond.target)
		if !decided {
			return "failed", nil
		}
		if !holds {
			return "skipped", nil
		}
	}
	return change(h, t)
}

// compare gives the truth of one condition, and false as its second result when it cannot be
// decided.
func compare(fact, operator, value string) (bool, bool) {
	switch operator {
	case "==":
		return fact == value, true
	case "!=":
		return fact != value, true
	}
	if !whole.MatchString(fact) || !whole.MatchString(value) {
		return false, false
	}
	left, _ := strconv.ParseInt(fact, 10, 64)
	right, _ := strconv.ParseInt(value, 10, 64)
	switch operator {
	case "<":
		return left < right, true
	case "<=":
		return left <= right, true
	case ">":
		return left > right, true
	default:
		return left >= right, true
	}
}

// current is the state a task of this kind compares with; false for a missing service.
func current(h *host, kind, target string) (string, bool) {
	switch kind {
	case "file":
		return h.files[target], true
	case "package":
		if _, ok := h.packages[target]; ok {
			return "present", true
		}
		return "absent", true
	}
	service, ok := h.packages[target]
	return service, ok
}

func change(h *host, a action) (string, []string) {
	before, ok := current(h, a.kind, a.target)
	if !ok {
		return "failed", nil
	}
	if before == a.value && a.value != "restarted" {
		return "ok", nil
	}
	apply(h, a.kind, a.target, a.value)
	return "changed", []string{before, a.value}
}

func apply(h *host, kind, target, value string) {
	switch {
	case kind == "file":
		h.files[target] = value
	case kind == "package" && value == "present":
		if _, ok := h.packages[target]; !ok {
			h.packages[target] = "stopped"
		}
	case kind == "package":
		delete(h.packages, target)
	case value == "restarted":
		h.packages[target] = "running"
	default:
		h.packages[target] = value
	}
}
