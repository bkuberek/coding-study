package unique_paths

const mod = 1_000_000_007

func uniquePaths(m int, n int) int {
	// A route is a sequence of m + n - 2 moves; choose which of them are the shorter direction.
	moves := m + n - 2
	chosen := min(m, n) - 1
	numerator, denominator := 1, 1
	for step := 1; step <= chosen; step++ {
		numerator = numerator * (moves - chosen + step) % mod
		denominator = denominator * step % mod
	}
	// mod is prime, so denominator^(mod-2) is its inverse (Fermat's little theorem).
	return numerator * modPow(denominator, mod-2) % mod
}

// modPow returns base^exponent mod `mod` by square-and-multiply; products stay below 2^63.
func modPow(base, exponent int) int {
	result := 1
	base %= mod
	for exponent > 0 {
		if exponent&1 == 1 {
			result = result * base % mod
		}
		base = base * base % mod
		exponent >>= 1
	}
	return result
}
