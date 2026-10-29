package car_fleet

func carFleet(target int, position []int, speed []int) int {
	// Arrival times are distance / speed; compare them by cross-multiplying, so no division.
	arrivesLater := func(car, other int) bool {
		return (target-position[car])*speed[other] > (target-position[other])*speed[car]
	}
	fleets := 0
	for car, mile := range position {
		slowest := -1
		for other, otherMile := range position {
			if otherMile > mile && (slowest < 0 || arrivesLater(other, slowest)) {
				slowest = other
			}
		}
		// The car leads its own fleet only if it arrives strictly later than the slowest car ahead.
		if slowest < 0 || arrivesLater(car, slowest) {
			fleets++
		}
	}
	return fleets
}
