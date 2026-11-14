package interval_list_intersections

func intervalIntersection(firstList [][]int, secondList [][]int) [][]int {
	var common [][]int
	i, j := 0, 0
	for i < len(firstList) && j < len(secondList) {
		start := max(firstList[i][0], secondList[j][0])
		end := min(firstList[i][1], secondList[j][1])
		if start <= end {
			common = append(common, []int{start, end})
		}
		// The interval that ends first cannot meet anything later in the other list.
		if firstList[i][1] < secondList[j][1] {
			i++
		} else {
			j++
		}
	}
	return common
}
