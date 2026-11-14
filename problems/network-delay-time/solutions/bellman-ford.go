package network_delay_time

import "math"

const unreached = math.MaxInt

func networkDelayTime(times [][]int, n int, k int) int {
	arrival := make([]int, n+1)
	for node := range arrival {
		arrival[node] = unreached
	}
	arrival[k] = 0
	// After round i, every node whose fastest route uses at most i links has its final time;
	// a fastest route has at most n - 1 links, and a round without changes ends early.
	for round := 0; round < n-1; round++ {
		changed := false
		for _, link := range times {
			u, v, w := link[0], link[1], link[2]
			// An unreached node offers nothing, and adding to the marker would overflow.
			if arrival[u] != unreached && arrival[u]+w < arrival[v] {
				arrival[v] = arrival[u] + w
				changed = true
			}
		}
		if !changed {
			break
		}
	}
	latest := 0
	for _, time := range arrival[1:] {
		latest = max(latest, time)
	}
	if latest == unreached {
		return -1
	}
	return latest
}
