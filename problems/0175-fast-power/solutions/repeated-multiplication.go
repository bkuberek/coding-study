package fast_power

import "math"

func myPow(x float64, n int) float64 {
	base := x
	if n < 0 {
		base = 1 / x
	}
	remaining := n
	if remaining < 0 {
		remaining = -remaining
	}
	result := 1.0
	done := 0
	for done < remaining {
		result *= base
		done++
		if result == 1.0 {
			// base^done == 1, so the powers repeat with period done (x = 1 or x = -1).
			remaining = (remaining - done) % done
			done = 0
		} else if result == 0.0 || math.IsInf(result, 0) {
			break // further multiplications cannot change the result
		}
	}
	return result
}
