package first_bad_commit

const (
	good = 0
	bad  = 1
)

func firstBadCommit(statuses []int) []int {
	lastGood := -1
	for position, status := range statuses {
		switch status {
		case good:
			lastGood = position
		case bad:
			return []int{lastGood + 1, position}
		}
	}
	panic("the history has no bad commit")
}
