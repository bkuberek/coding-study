// Counting in Go: a map counts, but ranging over a map visits keys in an unspecified order, so a
// ranking sorts explicitly, with a tie-break, to give the same answer every run.
package main

import (
	"cmp"
	"fmt"
	"maps"
	"slices"
	"strings"
)

func main() {
	log := strings.Fields("warn info info error info debug warn info error warn trace info")
	counts := map[string]int{}
	for _, level := range log {
		counts[level]++ // a missing key reads as 0, the zero value of int
	}
	fmt.Println("fmt prints a map sorted by key:", counts)

	levels := slices.Collect(maps.Keys(counts))
	slices.SortFunc(levels, func(a, b string) int {
		if byCount := cmp.Compare(counts[b], counts[a]); byCount != 0 {
			return byCount // more frequent first
		}
		return cmp.Compare(a, b) // then alphabetical, so ties are stable
	})
	for rank, level := range levels[:4] {
		fmt.Printf("%d. %s %d\n", rank+1, level, counts[level])
	}
}
