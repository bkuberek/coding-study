// With unsigned indexes, a bound cannot go below zero: 0 - 1 wraps around to the largest value.
// Go's unsigned arithmetic wraps silently, so the bug shows up later, as an index far out of range.
package main

import (
	"fmt"
	"math"
)

func closedSearch(values []int, target int) {
	lo, hi := uint64(0), uint64(len(values))-1
	for lo <= hi {
		mid := lo + (hi-lo)/2
		fmt.Printf("  lo %d  hi %d  mid %d  value %d\n", lo, hi, mid, values[mid])
		if values[mid] == target {
			fmt.Println("  found")
			return
		}
		if values[mid] < target {
			lo = mid + 1
		} else {
			hi = mid - 1
		}
		if hi == math.MaxUint64 {
			fmt.Printf("  hi = mid - 1 wrapped to %d, so lo <= hi still holds\n", hi)
			fmt.Println("  the next step would index values with a number that large: a panic")
			return
		}
	}
	fmt.Println("  absent")
}

// The half-open version never subtracts from a bound, so it has nothing to wrap.
func halfOpenSearch(values []int, target int) string {
	lo, hi := uint64(0), uint64(len(values))
	for lo < hi {
		mid := lo + (hi-lo)/2
		if values[mid] == target {
			return fmt.Sprintf("found at %d", mid)
		}
		if values[mid] < target {
			lo = mid + 1
		} else {
			hi = mid
		}
	}
	return "absent"
}

func main() {
	values := []int{10, 20, 30, 40, 50}
	fmt.Println("closed interval, unsigned indexes, searching for 5:")
	closedSearch(values, 5)

	var empty []int
	fmt.Println("an empty slice: uint64(len(empty)) - 1 =", uint64(len(empty))-1)

	fmt.Println("half-open, searching for 5:", halfOpenSearch(values, 5))
	fmt.Println("half-open, searching for 40:", halfOpenSearch(values, 40))
	fmt.Println("half-open, empty slice:", halfOpenSearch(empty, 5))
}
