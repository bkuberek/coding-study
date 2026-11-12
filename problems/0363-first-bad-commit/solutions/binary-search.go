package first_bad_commit

const (
	bad  = 1
	skip = 2
)

func firstBadCommit(statuses []int) []int {
	firstBad := findFirstBad(statuses)
	lastGood := findLastGoodBefore(statuses, firstBad)
	return []int{lastGood + 1, firstBad}
}

// findFirstBad returns the first bad commit. Some commit is bad, so it lies in [low, high].
func findFirstBad(statuses []int) int {
	low, high := 0, len(statuses)-1
	for low < high {
		middle := low + (high-low)/2
		probe := middle
		for probe >= low && statuses[probe] == skip {
			probe--
		}
		if probe >= low && statuses[probe] == bad {
			high = probe
		} else {
			low = middle + 1
		}
	}
	return low
}

// findLastGoodBefore returns the last good commit before firstBad, or -1 when there is none.
// Every commit before the first bad one that was tested is good.
func findLastGoodBefore(statuses []int, firstBad int) int {
	low, high := -1, firstBad-1
	for low < high {
		middle := (low + high + 1) / 2
		probe := middle
		for probe <= high && statuses[probe] == skip {
			probe++
		}
		if probe <= high {
			low = probe
		} else {
			high = middle - 1
		}
	}
	return low
}
