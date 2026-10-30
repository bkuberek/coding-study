package fast_power

func myPow(x float64, n int) float64 {
	if n < 0 {
		x, n = 1/x, -n
	}
	result := 1.0
	// Invariant: result * x^n equals the original x^n.
	for n > 0 {
		if n&1 == 1 {
			result *= x
		}
		x *= x
		n >>= 1
	}
	return result
}
