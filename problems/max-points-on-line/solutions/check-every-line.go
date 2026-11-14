package max_points_on_line

func maxPoints(points [][]int) int {
	if len(points) <= 2 {
		return len(points)
	}
	best := 2
	for i, first := range points {
		x1, y1 := first[0], first[1]
		for _, second := range points[i+1:] {
			dx, dy := second[0]-x1, second[1]-y1
			// (x, y) is on the line through both points when the cross product is zero.
			onLine := 0
			for _, point := range points {
				if dy*(point[0]-x1) == dx*(point[1]-y1) {
					onLine++
				}
			}
			best = max(best, onLine)
		}
	}
	return best
}
