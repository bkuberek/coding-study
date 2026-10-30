// Debug: Append Aliasing. Some tests fail: find the bug and fix it.
package debug_append_aliasing

func bundleCombos(items []int, size int) [][]int {
	var bundles [][]int
	var extend func(start int, bundle []int)
	extend = func(start int, bundle []int) {
		if len(bundle) == size {
			bundles = append(bundles, bundle)
			return
		}
		for i := start; i < len(items); i++ {
			extend(i+1, append(bundle, items[i]))
		}
	}
	extend(0, nil)
	return bundles
}
