package jump_game

func canJump(nums []int) bool {
	goal := len(nums) - 1 // the leftmost index known to reach the last index
	for i := len(nums) - 2; i >= 0; i-- {
		if i+nums[i] >= goal {
			goal = i
		}
	}
	return goal == 0
}
