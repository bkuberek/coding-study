package car_pooling

import (
	"cmp"
	"slices"
)

type event struct {
	location, change int
}

func carPooling(trips [][]int, capacity int) bool {
	events := make([]event, 0, 2*len(trips))
	for _, trip := range trips {
		passengers, start, end := trip[0], trip[1], trip[2]
		events = append(events, event{start, passengers}, event{end, -passengers})
	}
	// Sort by location, then by change: drop-offs (negative) come before pickups.
	slices.SortFunc(events, func(a, b event) int {
		return cmp.Or(cmp.Compare(a.location, b.location), cmp.Compare(a.change, b.change))
	})
	load := 0
	for _, e := range events {
		load += e.change
		if load > capacity {
			return false
		}
	}
	return true
}
