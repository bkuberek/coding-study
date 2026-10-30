package max_points_on_line

// gcd returns the greatest common divisor of a and b as a non-negative number.
func gcd(a, b int) int {
	for b != 0 {
		a, b = b, a%b
	}
	if a < 0 {
		return -a
	}
	return a
}

func maxPoints(points [][]int) int {
	best := 1
	for i, anchor := range points {
		directions := make(map[[2]int]int)
		for _, other := range points[i+1:] {
			dx, dy := other[0]-anchor[0], other[1]-anchor[1]
			divisor := gcd(dx, dy) // never 0: the points are distinct
			dx, dy = dx/divisor, dy/divisor
			// One representative per direction: dx > 0, or dx == 0 and dy > 0.
			if dx < 0 || (dx == 0 && dy < 0) {
				dx, dy = -dx, -dy
			}
			directions[[2]int{dx, dy}]++
		}
		for _, count := range directions {
			best = max(best, count+1) // + 1 for the anchor
		}
	}
	return best
}
