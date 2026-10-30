package network_delay_time

import "math"

const unreached = math.MaxInt

type link struct{ to, weight int }

func networkDelayTime(times [][]int, n int, k int) int {
	graph := make([][]link, n+1)
	for _, entry := range times {
		graph[entry[0]] = append(graph[entry[0]], link{entry[1], entry[2]})
	}
	arrival := make([]int, n+1)
	for node := range arrival {
		arrival[node] = unreached
	}
	arrival[k] = 0
	settled := make([]bool, n+1)
	latest := 0
	for round := 0; round < n; round++ {
		// Scan for the unsettled node with the earliest arrival: O(n) per round, no heap.
		node := 0
		for candidate := 1; candidate <= n; candidate++ {
			if !settled[candidate] && (node == 0 || arrival[candidate] < arrival[node]) {
				node = candidate
			}
		}
		if arrival[node] == unreached {
			return -1
		}
		settled[node] = true
		latest = arrival[node]
		for _, next := range graph[node] {
			arrival[next.to] = min(arrival[next.to], arrival[node]+next.weight)
		}
	}
	return latest
}
