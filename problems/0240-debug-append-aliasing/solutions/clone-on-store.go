package debug_append_aliasing

import "slices"

func bundleCombos(items []int, size int) [][]int {
	var bundles [][]int
	var extend func(start int, bundle []int)
	extend = func(start int, bundle []int) {
		if len(bundle) == size {
			// bundle shares its backing array with its siblings; store a copy it owns.
			bundles = append(bundles, slices.Clone(bundle))
			return
		}
		for i := start; i < len(items); i++ {
			extend(i+1, append(bundle, items[i]))
		}
	}
	extend(0, nil)
	return bundles
}
