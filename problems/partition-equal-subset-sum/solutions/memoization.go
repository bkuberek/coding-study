package partition_equal_subset_sum

const (
	unknown int8 = iota
	reachableSum
	unreachableSum
)

func canPartition(nums []int) bool {
	total := 0
	for _, value := range nums {
		total += value
	}
	if total%2 == 1 {
		return false
	}
	target := total / 2
	// memo[index][remaining] is unknown until that state has been decided.
	memo := make([][]int8, len(nums))
	for index := range memo {
		memo[index] = make([]int8, target+1)
	}

	// reachable reports whether some elements of nums[index:] add up to exactly remaining.
	var reachable func(index, remaining int) bool
	reachable = func(index, remaining int) bool {
		if remaining == 0 {
			return true
		}
		if index == len(nums) || remaining < 0 {
			return false
		}
		if memo[index][remaining] == unknown {
			if reachable(index+1, remaining-nums[index]) || reachable(index+1, remaining) {
				memo[index][remaining] = reachableSum
			} else {
				memo[index][remaining] = unreachableSum
			}
		}
		return memo[index][remaining] == reachableSum
	}

	return reachable(0, target)
}
