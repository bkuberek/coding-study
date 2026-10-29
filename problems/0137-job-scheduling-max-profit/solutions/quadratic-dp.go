package job_scheduling_max_profit

import "sort"

type job struct{ end, start, profit int }

func jobScheduling(startTime []int, endTime []int, profit []int) int {
	jobs := make([]job, len(startTime))
	for i := range jobs {
		jobs[i] = job{endTime[i], startTime[i], profit[i]}
	}
	sort.Slice(jobs, func(a, b int) bool { return jobs[a].end < jobs[b].end })
	// best[i] is the most profit from the first i jobs in end-time order.
	best := make([]int, len(jobs)+1)
	for i, current := range jobs {
		// Walk back to the last job that ends no later than this one starts.
		compatible := i - 1
		for compatible >= 0 && jobs[compatible].end > current.start {
			compatible--
		}
		best[i+1] = max(best[i], current.profit+best[compatible+1])
	}
	return best[len(jobs)]
}
