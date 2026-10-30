package network_delay_time

import "container/heap"

type link struct{ to, weight int }

// entry is a candidate arrival: the node would be reached at this time.
type entry struct{ time, node int }

// entryHeap is a binary min-heap of entries ordered by time.
type entryHeap []entry

func (h entryHeap) Len() int           { return len(h) }
func (h entryHeap) Less(a, b int) bool { return h[a].time < h[b].time }
func (h entryHeap) Swap(a, b int)      { h[a], h[b] = h[b], h[a] }
func (h *entryHeap) Push(x any)        { *h = append(*h, x.(entry)) }
func (h *entryHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

func networkDelayTime(times [][]int, n int, k int) int {
	graph := make([][]link, n+1)
	for _, record := range times {
		graph[record[0]] = append(graph[record[0]], link{record[1], record[2]})
	}
	settled := make([]bool, n+1)
	reached, latest := 0, 0
	queue := &entryHeap{{0, k}}
	for queue.Len() > 0 {
		current := heap.Pop(queue).(entry)
		if settled[current.node] {
			continue // an outdated entry: the node was settled earlier with a smaller time
		}
		settled[current.node] = true
		reached++
		latest = max(latest, current.time)
		for _, next := range graph[current.node] {
			if !settled[next.to] {
				heap.Push(queue, entry{current.time + next.weight, next.to})
			}
		}
	}
	if reached != n {
		return -1
	}
	return latest
}
