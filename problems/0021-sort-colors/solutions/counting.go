package sort_colors

func sortColors(nums []int) {
	var counts [3]int
	for _, color := range nums {
		counts[color]++
	}
	index := 0
	for color, count := range counts {
		for range count {
			nums[index] = color
			index++
		}
	}
}
