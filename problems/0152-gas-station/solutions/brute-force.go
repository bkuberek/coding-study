package gas_station

func canCompleteCircuit(gas []int, cost []int) int {
	n := len(gas)
	for start := 0; start < n; start++ {
		fuel := 0
		completed := true
		for step := 0; step < n; step++ {
			station := (start + step) % n
			fuel += gas[station] - cost[station]
			if fuel < 0 {
				completed = false
				break
			}
		}
		if completed {
			return start
		}
	}
	return -1
}
