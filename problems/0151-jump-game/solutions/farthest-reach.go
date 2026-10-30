package jump_game

func canJump(nums []int) bool {
	farthest := 0 // every index up to `farthest` is reachable
	for i, jump := range nums {
		if i > farthest {
			return false
		}
		farthest = max(farthest, i+jump)
	}
	return true
}
