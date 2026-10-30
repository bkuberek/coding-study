package jump_game

func canJump(nums []int) bool {
	last := len(nums) - 1
	// reachable[i] is true once some sequence of jumps from index 0 is known to land on i.
	reachable := make([]bool, len(nums))
	reachable[0] = true
	for i := range nums {
		if !reachable[i] {
			continue
		}
		if i == last {
			return true
		}
		for target := i + 1; target <= min(last, i+nums[i]); target++ {
			reachable[target] = true
		}
	}
	return reachable[last]
}
