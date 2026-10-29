package remove_k_digits

import (
	"slices"
	"strings"
)

func removeKDigits(num string, k int) string {
	digits := []byte(num)
	for range k {
		// The first digit larger than its successor, or the last digit if none is.
		peak := 0
		for peak+1 < len(digits) && digits[peak] <= digits[peak+1] {
			peak++
		}
		digits = slices.Delete(digits, peak, peak+1)
	}
	if trimmed := strings.TrimLeft(string(digits), "0"); trimmed != "" {
		return trimmed
	}
	return "0"
}
