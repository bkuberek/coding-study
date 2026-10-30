package sum_without_plus

func getSum(a int, b int) int {
	// Work on the 32-bit patterns: a uint32 drops the bit shifted out of position 31, so a
	// negative carry dies out instead of growing.
	x, y := uint32(a), uint32(b)
	for y != 0 {
		carry := (x & y) << 1
		x ^= y // the sum of every column, ignoring carries
		y = carry
	}
	// A set sign bit means a negative value: reading the pattern as an int32 recovers it.
	return int(int32(x))
}
