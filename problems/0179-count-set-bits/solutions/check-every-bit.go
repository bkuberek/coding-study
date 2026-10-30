package count_set_bits

const wordBits = 32

func hammingWeight(n int64) int {
	count := 0
	for position := 0; position < wordBits; position++ {
		count += int((n >> position) & 1)
	}
	return count
}
