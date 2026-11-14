package counting_bits

func countBits(n int) []int {
	bits := make([]int, n+1)
	for i := 1; i <= n; i++ {
		// i >> 1 drops the lowest bit of i and is smaller than i, so its count is known.
		bits[i] = bits[i>>1] + (i & 1)
	}
	return bits
}
