package stream_windows

import "sort"

type event struct{ key, time, value int }

type window struct{ start, key int }

type totals struct{ count, sum int }

func bump(groups map[window]*totals, w window, value int) {
	t, ok := groups[w]
	if !ok {
		t = &totals{}
		groups[w] = t
	}
	t.count++
	t.sum += value
}

func sortedWindows(groups map[window]*totals) []window {
	ws := make([]window, 0, len(groups))
	for w := range groups {
		ws = append(ws, w)
	}
	sort.Slice(ws, func(i, j int) bool {
		if ws[i].start != ws[j].start {
			return ws[i].start < ws[j].start
		}
		return ws[i].key < ws[j].key
	})
	return ws
}

func row(w window, size, count, sum int) []int {
	return []int{w.key, w.start, w.start + size, count, sum}
}

func rows(groups map[window]*totals, size int) [][]int {
	out := [][]int{}
	for _, w := range sortedWindows(groups) {
		out = append(out, row(w, size, groups[w].count, groups[w].sum))
	}
	return out
}

// StreamWindows keeps every event in a log, so the batch views of levels 1 and 2 can group the
// whole stream in any way they are asked.
//
// The stream of levels 3 and 4 keeps a map from (start, key) to a running count and sum for the
// windows not yet emitted, and a second map for the windows already emitted that can still be
// corrected. After each event the watermark moves, the open windows it has passed are emitted in
// order, and the corrected windows it has left behind are forgotten.
type StreamWindows struct {
	events   []event
	size     int
	lateness int
	grace    int
	mark     int
	open     map[window]*totals
	closed   map[window]*totals
	out      [][]int
	side     [][]int
	emitted  int
	updated  int
}

func NewStreamWindows() *StreamWindows {
	return &StreamWindows{open: map[window]*totals{}, closed: map[window]*totals{}}
}

// Level 1
func (s *StreamWindows) Add(key int, time int, value int) {
	s.events = append(s.events, event{key, time, value})
	if s.size > 0 {
		s.stream(key, time, value)
	}
}

func (s *StreamWindows) Tumbling(size int) [][]int {
	groups := map[window]*totals{}
	for _, e := range s.events {
		bump(groups, window{e.time - e.time%size, e.key}, e.value)
	}
	return rows(groups, size)
}

// Level 2
func (s *StreamWindows) Hopping(size int, slide int) [][]int {
	groups := map[window]*totals{}
	for _, e := range s.events {
		for start := e.time - e.time%slide; start > e.time-size; start -= slide {
			bump(groups, window{start, e.key}, e.value)
		}
	}
	return rows(groups, size)
}

func (s *StreamWindows) Sessions(gap int) [][]int {
	byKey := map[int][]event{}
	for _, e := range s.events {
		byKey[e.key] = append(byKey[e.key], e)
	}
	sessions := [][]int{}
	for key, list := range byKey {
		sort.SliceStable(list, func(i, j int) bool { return list[i].time < list[j].time })
		var current []int
		for _, e := range list {
			if current != nil && e.time < current[2] {
				current[2] = e.time + gap
				current[3]++
				current[4] += e.value
			} else {
				current = []int{key, e.time, e.time + gap, 1, e.value}
				sessions = append(sessions, current)
			}
		}
	}
	sort.Slice(sessions, func(i, j int) bool {
		if sessions[i][1] != sessions[j][1] {
			return sessions[i][1] < sessions[j][1]
		}
		return sessions[i][0] < sessions[j][0]
	})
	return sessions
}

// Level 3
func (s *StreamWindows) Configure(size int, lateness int) {
	s.size = size
	s.lateness = lateness
}

func (s *StreamWindows) Watermark() int {
	return s.mark
}

func (s *StreamWindows) Pending() [][]int {
	return rows(s.open, s.size)
}

func (s *StreamWindows) Poll() [][]int {
	out := s.out
	s.out = nil
	return out
}

// Level 4
func (s *StreamWindows) AllowUpdates(grace int) {
	s.grace = grace
}

func (s *StreamWindows) Dropped() [][]int {
	return append([][]int{}, s.side...)
}

func (s *StreamWindows) Stats() []int {
	return []int{s.emitted, s.updated, len(s.side)}
}

// The stream
func (s *StreamWindows) stream(key, time, value int) {
	start := time - time%s.size
	end := start + s.size
	w := window{start, key}
	switch {
	case end > s.mark:
		bump(s.open, w, value)
	case s.mark < end+s.grace:
		s.correct(w, value)
	default:
		s.side = append(s.side, []int{key, time, value})
	}
	s.advance(time - s.lateness)
}

func (s *StreamWindows) correct(w window, value int) {
	old, ok := s.closed[w]
	if !ok {
		s.closed[w] = &totals{1, value}
		s.emitted++
		s.out = append(s.out, row(w, s.size, 1, value))
		return
	}
	s.out = append(s.out, row(w, s.size, -old.count, -old.sum))
	old.count++
	old.sum += value
	s.updated++
	s.out = append(s.out, row(w, s.size, old.count, old.sum))
}

func (s *StreamWindows) advance(candidate int) {
	if candidate <= s.mark {
		return
	}
	s.mark = candidate
	due := map[window]*totals{}
	for w, t := range s.open {
		if w.start+s.size <= s.mark {
			due[w] = t
		}
	}
	for _, w := range sortedWindows(due) {
		t := due[w]
		delete(s.open, w)
		s.out = append(s.out, row(w, s.size, t.count, t.sum))
		s.closed[w] = t
		s.emitted++
	}
	for w := range s.closed {
		if w.start+s.size+s.grace <= s.mark {
			delete(s.closed, w)
		}
	}
}
