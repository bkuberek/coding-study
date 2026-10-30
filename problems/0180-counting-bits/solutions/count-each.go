package counting_bits

func countBits(n int) []int {
	bits := make([]int, n+1)
	for i := 0; i <= n; i++ {
		count := 0
		for word := i; word != 0; word &= word - 1 {
			count++ // each step clears the lowest set bit
		}
		bits[i] = count
	}
	return bits
}
