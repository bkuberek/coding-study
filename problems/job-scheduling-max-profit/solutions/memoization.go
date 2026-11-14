package job_scheduling_max_profit

import "sort"

type job struct{ start, end, profit int }

func jobScheduling(startTime []int, endTime []int, profit []int) int {
	jobs := make([]job, len(startTime))
	for i := range jobs {
		jobs[i] = job{startTime[i], endTime[i], profit[i]}
	}
	sort.Slice(jobs, func(a, b int) bool { return jobs[a].start < jobs[b].start })
	// memo[index] is the most profit from jobs[index:], or -1 while unknown.
	memo := make([]int, len(jobs))
	for i := range memo {
		memo[i] = -1
	}
	var bestFrom func(index int) int
	bestFrom = func(index int) int {
		if index == len(jobs) {
			return 0
		}
		if memo[index] == -1 {
			current := jobs[index]
			// The first job after this one that starts once this one has ended.
			following := index + 1 + sort.Search(len(jobs)-index-1, func(k int) bool {
				return jobs[index+1+k].start >= current.end
			})
			memo[index] = max(bestFrom(index+1), current.profit+bestFrom(following))
		}
		return memo[index]
	}
	return bestFrom(0)
}
