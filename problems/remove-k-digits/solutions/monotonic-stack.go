package remove_k_digits

import "strings"

func removeKDigits(num string, k int) string {
	// The digits kept so far; they never decrease from bottom to top.
	kept := make([]byte, 0, len(num))
	remaining := k
	for i := 0; i < len(num); i++ {
		digit := num[i]
		for remaining > 0 && len(kept) > 0 && kept[len(kept)-1] > digit {
			kept = kept[:len(kept)-1]
			remaining--
		}
		kept = append(kept, digit)
	}
	// The kept digits never decrease, so leftover deletions are cheapest at the end.
	kept = kept[:len(kept)-remaining]
	if trimmed := strings.TrimLeft(string(kept), "0"); trimmed != "" {
		return trimmed
	}
	return "0"
}
