package task_scheduler

import "slices"

func leastInterval(tasks []rune, cooldown int) int {
	var counts [26]int
	for _, task := range tasks {
		counts[task-'A']++
	}
	top := slices.Max(counts[:])
	tied := 0
	for _, count := range counts {
		if count == top {
			tied++
		}
	}
	// top - 1 full frames of cooldown + 1 slots, then one last partial frame holding the
	// tied most frequent tasks. With enough other tasks, no slot idles and the answer is
	// simply the number of tasks.
	return max(len(tasks), (top-1)*(cooldown+1)+tied)
}
