package interval_list_intersections

import "sort"

func intervalIntersection(firstList [][]int, secondList [][]int) [][]int {
	var common [][]int
	for _, first := range firstList {
		firstStart, firstEnd := first[0], first[1]
		// The first interval of secondList that ends at or after firstStart.
		partner := sort.Search(len(secondList), func(i int) bool { return secondList[i][1] >= firstStart })
		for ; partner < len(secondList) && secondList[partner][0] <= firstEnd; partner++ {
			common = append(common, []int{
				max(firstStart, secondList[partner][0]),
				min(firstEnd, secondList[partner][1]),
			})
		}
	}
	return common
}
