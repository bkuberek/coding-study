package interval_list_intersections

func intervalIntersection(firstList [][]int, secondList [][]int) [][]int {
	// Both lists are sorted and separate, so pairs taken in this order yield sorted output.
	var common [][]int
	for _, first := range firstList {
		for _, second := range secondList {
			start, end := max(first[0], second[0]), min(first[1], second[1])
			if start <= end {
				common = append(common, []int{start, end})
			}
		}
	}
	return common
}
