package candy_distribution

func candy(ratings []int) int {
	total := 1
	up := 0   // length of the current rising run: the latest child got up + 1 candies
	down := 0 // length of the current falling run
	peak := 0 // the rising run length at the top of the current peak
	for i := 1; i < len(ratings); i++ {
		switch {
		case ratings[i] > ratings[i-1]:
			up++
			peak = up
			down = 0
			total += up + 1
		case ratings[i] == ratings[i-1]:
			up, down, peak = 0, 0, 0
			total++
		default:
			up = 0
			down++
			// Every child on the falling run gets one more candy; the peak only needs one
			// more once the falling run is longer than the rising run that built it.
			total += down
			if down > peak {
				total++
			}
		}
	}
	return total
}
