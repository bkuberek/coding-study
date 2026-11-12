// On the answer, the "array" is a range of values. sort.Search walks any range [0, n) with a
// predicate, and a value range can be large enough for lo + hi to overflow an int64.
package main

import (
	"fmt"
	"sort"
)

var posts = []int{0, 3, 4, 7, 11, 12, 18, 20, 25}

// fits reports whether k sensors can stand on posts with every two at least gap apart.
func fits(gap, k int) bool {
	count, last := 1, posts[0]
	for _, post := range posts[1:] {
		if post-last >= gap {
			count, last = count+1, post
		}
	}
	return count >= k
}

func main() {
	span := posts[len(posts)-1] - posts[0]
	// The smallest gap in [0, span + 1) that is too wide: sort.Search's index is a gap here.
	firstTooWide := sort.Search(span+1, func(gap int) bool { return !fits(gap, 4) })
	fmt.Println("largest gap for 4 sensors:", firstTooWide-1)

	lo, hi := int64(5_000_000_000_000_000_000), int64(9_000_000_000_000_000_000)
	fmt.Println("(lo + hi) / 2      =", (lo+hi)/2)
	fmt.Println("lo + (hi - lo) / 2 =", lo+(hi-lo)/2)

	// The first value of at least the threshold in [lo, hi): 62 steps cover four quintillion values.
	threshold := int64(7_123_456_789_012_345_678)
	steps := 0
	for lo < hi {
		mid := lo + (hi-lo)/2
		if mid >= threshold {
			hi = mid
		} else {
			lo = mid + 1
		}
		steps++
	}
	fmt.Println("found", lo, "in", steps, "steps")
}
