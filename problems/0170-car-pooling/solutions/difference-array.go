package car_pooling

func carPooling(trips [][]int, capacity int) bool {
	last := 0
	for _, trip := range trips {
		last = max(last, trip[2])
	}
	// change[x] is how much the load changes at location x; its prefix sums are the loads.
	change := make([]int, last+1)
	for _, trip := range trips {
		passengers, start, end := trip[0], trip[1], trip[2]
		change[start] += passengers
		change[end] -= passengers
	}
	load := 0
	for _, delta := range change {
		load += delta
		if load > capacity {
			return false
		}
	}
	return true
}
