package k_closest_points

import "math/rand/v2"

func kClosest(points [][]int, k int) [][]int {
	distance := make([]int, len(points))
	order := make([]int, len(points))
	for i, point := range points {
		distance[i] = point[0]*point[0] + point[1]*point[1]
		order[i] = i
	}
	low, high := 0, len(order)-1
	// Partition until position k - 1 holds its sorted entry; then positions 0..k-1 hold
	// the k closest points (in some order).
	for low < high {
		pivot := distance[order[low+rand.IntN(high-low+1)]]
		less, scan, greater := low, low, high
		for scan <= greater {
			value := distance[order[scan]]
			switch {
			case value < pivot:
				order[less], order[scan] = order[scan], order[less]
				less++
				scan++
			case value > pivot:
				order[scan], order[greater] = order[greater], order[scan]
				greater--
			default:
				scan++
			}
		}
		if k-1 < less {
			high = less - 1
		} else if k-1 > greater {
			low = greater + 1
		} else {
			break
		}
	}
	closest := make([][]int, k)
	for i, position := range order[:k] {
		closest[i] = points[position]
	}
	return closest
}
