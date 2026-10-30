package car_pooling

func carPooling(trips [][]int, capacity int) bool {
	// The load is highest right after some pickup, so checking every pickup point suffices.
	busiest := 0
	for _, pickupTrip := range trips {
		pickup := pickupTrip[1]
		load := 0
		for _, trip := range trips {
			if trip[1] <= pickup && pickup < trip[2] {
				load += trip[0]
			}
		}
		busiest = max(busiest, load)
	}
	return busiest <= capacity
}
