package range_module

type interval struct {
	start, end int
}

type RangeModule struct {
	// Disjoint, non-touching half-open intervals, sorted by start.
	intervals []interval
}

func NewRangeModule() *RangeModule {
	return &RangeModule{}
}

func (m *RangeModule) AddRange(left int, right int) {
	merged := make([]interval, 0, len(m.intervals)+1)
	placed := false
	for _, current := range m.intervals {
		switch {
		case current.end < left:
			merged = append(merged, current)
		case right < current.start:
			if !placed {
				merged = append(merged, interval{left, right})
				placed = true
			}
			merged = append(merged, current)
		default:
			// Overlapping or touching: absorb it into the new interval.
			left, right = min(left, current.start), max(right, current.end)
		}
	}
	if !placed {
		merged = append(merged, interval{left, right})
	}
	m.intervals = merged
}

func (m *RangeModule) QueryRange(left int, right int) bool {
	// Stored intervals never touch, so a covered range lies inside a single one.
	for _, current := range m.intervals {
		if current.start <= left && right <= current.end {
			return true
		}
	}
	return false
}

func (m *RangeModule) RemoveRange(left int, right int) {
	kept := make([]interval, 0, len(m.intervals)+1)
	for _, current := range m.intervals {
		if current.end <= left || right <= current.start {
			kept = append(kept, current)
			continue
		}
		if current.start < left {
			kept = append(kept, interval{current.start, left})
		}
		if right < current.end {
			kept = append(kept, interval{right, current.end})
		}
	}
	m.intervals = kept
}
