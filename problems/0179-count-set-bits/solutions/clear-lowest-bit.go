package count_set_bits

func hammingWeight(n int64) int {
	// The low 32 bits as an unsigned word: the input is below 2^32, so nothing is lost.
	word := uint32(n)
	count := 0
	for word != 0 {
		word &= word - 1 // clears the lowest set bit
		count++
	}
	return count
}
