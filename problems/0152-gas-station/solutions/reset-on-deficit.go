package gas_station

func canCompleteCircuit(gas []int, cost []int) int {
	total := 0 // fuel balance of the whole circle
	fuel := 0  // fuel since the current candidate start
	start := 0
	for station := range gas {
		surplus := gas[station] - cost[station]
		total += surplus
		fuel += surplus
		if fuel < 0 {
			// No station from `start` to `station` can be the answer; try the next one.
			start = station + 1
			fuel = 0
		}
	}
	if total >= 0 {
		return start
	}
	return -1
}
