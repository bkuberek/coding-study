package sum_without_plus

const wordBits = 32

func getSum(a int, b int) int {
	// The 32-bit two's complement patterns of the inputs: converting a negative int to uint32 wraps.
	x, y := uint32(a), uint32(b)
	var result, carry uint32
	for position := 0; position < wordBits; position++ {
		bitA, bitB := (x>>position)&1, (y>>position)&1
		result |= (bitA ^ bitB ^ carry) << position
		carry = (bitA & bitB) | (carry & (bitA ^ bitB)) // carry out: at least two of the three bits
	}
	// A set sign bit means a negative value: reading the pattern as an int32 recovers it.
	return int(int32(result))
}
