package logical_clocks

import "sort"

type stamp struct {
	process int
	lamport int
	vector  []int
	l       int64
	c       int64
	wall    int64
	isSend  bool
	value   string
}

// LogicalClocks keeps, for each process, the current value of its three clocks: a Lamport
// counter, a vector and a hybrid pair. Every event updates them by the rules of its kind and keeps
// a copy as its stamp, so every question afterwards is answered from the stamps alone.
type LogicalClocks struct {
	processes  int
	lamportNow []int
	vectorNow  [][]int
	hybridNow  [][2]int64
	events     map[string]*stamp
	received   map[string]bool
	writes     map[string][]string
}

func NewLogicalClocks(processes int) *LogicalClocks {
	vectors := make([][]int, processes)
	for i := range vectors {
		vectors[i] = make([]int, processes)
	}
	return &LogicalClocks{
		processes:  processes,
		lamportNow: make([]int, processes),
		vectorNow:  vectors,
		hybridNow:  make([][2]int64, processes),
		events:     map[string]*stamp{},
		received:   map[string]bool{},
		writes:     map[string][]string{},
	}
}

// Level 1
func (lc *LogicalClocks) Local(process int, event string, wall int64) int {
	return lc.record(process, event, wall, nil, false)
}

func (lc *LogicalClocks) Send(process int, event string, wall int64) int {
	return lc.record(process, event, wall, nil, true)
}

func (lc *LogicalClocks) Receive(process int, event string, message string, wall int64) int {
	sent, known := lc.events[message]
	if !known || !sent.isSend || lc.received[message] || sent.process == process {
		return -1
	}
	result := lc.record(process, event, wall, sent, false)
	if result != -1 {
		lc.received[message] = true
	}
	return result
}

func (lc *LogicalClocks) TotalOrder() []string {
	return lc.sortedBy(func(one, other *stamp) bool {
		if one.lamport != other.lamport {
			return one.lamport < other.lamport
		}
		return one.process < other.process
	})
}

// Level 2
func (lc *LogicalClocks) Vector(event string) []int {
	found, known := lc.events[event]
	if !known {
		return []int{}
	}
	return append([]int{}, found.vector...)
}

func (lc *LogicalClocks) Compare(first string, second string) string {
	one, knownFirst := lc.events[first]
	other, knownSecond := lc.events[second]
	switch {
	case !knownFirst || !knownSecond:
		return ""
	case first == second:
		return "same"
	case atMost(one.vector, other.vector):
		return "before"
	case atMost(other.vector, one.vector):
		return "after"
	default:
		return "concurrent"
	}
}

// Level 3
func (lc *LogicalClocks) Write(process int, event string, key string, value string, wall int64) int {
	result := lc.record(process, event, wall, nil, false)
	if result != -1 {
		lc.events[event].value = value
		lc.writes[key] = append(lc.writes[key], event)
	}
	return result
}

func (lc *LogicalClocks) Read(process int, key string) []string {
	values := []string{}
	if process < 0 || process >= lc.processes {
		return values
	}
	now := lc.vectorNow[process]
	known := []*stamp{}
	for _, name := range lc.writes[key] {
		if written := lc.events[name]; atMost(written.vector, now) {
			known = append(known, written)
		}
	}
	for _, written := range known {
		superseded := false
		for _, other := range known {
			if other != written && atMost(written.vector, other.vector) {
				superseded = true
				break
			}
		}
		if !superseded {
			values = append(values, written.value)
		}
	}
	sort.Strings(values)
	return values
}

func (lc *LogicalClocks) ConcurrentWrites(key string) [][]string {
	names := append([]string{}, lc.writes[key]...)
	sort.Strings(names)
	pairs := [][]string{}
	for i := range names {
		for j := i + 1; j < len(names); j++ {
			if lc.Compare(names[i], names[j]) == "concurrent" {
				pairs = append(pairs, []string{names[i], names[j]})
			}
		}
	}
	return pairs
}

// Level 4
func (lc *LogicalClocks) Hlc(event string) []int64 {
	found, known := lc.events[event]
	if !known {
		return []int64{}
	}
	return []int64{found.l, found.c}
}

func (lc *LogicalClocks) HlcOrder() []string {
	return lc.sortedBy(func(one, other *stamp) bool {
		if one.l != other.l {
			return one.l < other.l
		}
		if one.c != other.c {
			return one.c < other.c
		}
		return one.process < other.process
	})
}

func (lc *LogicalClocks) MaxOffset() int64 {
	var largest int64
	for _, found := range lc.events {
		if found.l-found.wall > largest {
			largest = found.l - found.wall
		}
	}
	return largest
}

// Shared
func atMost(first, second []int) bool {
	for i := range first {
		if first[i] > second[i] {
			return false
		}
	}
	return true
}

func (lc *LogicalClocks) sortedBy(less func(one, other *stamp) bool) []string {
	names := make([]string, 0, len(lc.events))
	for name := range lc.events {
		names = append(names, name)
	}
	sort.Slice(names, func(i, j int) bool { return less(lc.events[names[i]], lc.events[names[j]]) })
	return names
}

func (lc *LogicalClocks) record(process int, event string, wall int64, sent *stamp, isSend bool) int {
	if _, taken := lc.events[event]; taken || process < 0 || process >= lc.processes {
		return -1
	}
	lamport := lc.lamportNow[process]
	vector := append([]int{}, lc.vectorNow[process]...)
	if sent == nil {
		lamport++
	} else {
		lamport = max(lamport, sent.lamport) + 1
		for i := range vector {
			vector[i] = max(vector[i], sent.vector[i])
		}
	}
	vector[process]++
	hybrid := nextHybrid(lc.hybridNow[process], wall, sent)
	lc.lamportNow[process] = lamport
	lc.vectorNow[process] = vector
	lc.hybridNow[process] = hybrid
	lc.events[event] = &stamp{process, lamport, vector, hybrid[0], hybrid[1], wall, isSend, ""}
	return lamport
}

// nextHybrid is the update of Kulkarni et al.: l is the largest physical reading heard of, and c
// counts the events since l last changed.
func nextHybrid(current [2]int64, wall int64, sent *stamp) [2]int64 {
	oldL, oldC := current[0], current[1]
	if sent == nil {
		l := max(oldL, wall)
		if l == oldL {
			return [2]int64{l, oldC + 1}
		}
		return [2]int64{l, 0}
	}
	l := max(oldL, sent.l, wall)
	switch {
	case l == oldL && l == sent.l:
		return [2]int64{l, max(oldC, sent.c) + 1}
	case l == oldL:
		return [2]int64{l, oldC + 1}
	case l == sent.l:
		return [2]int64{l, sent.c + 1}
	default:
		return [2]int64{l, 0}
	}
}
