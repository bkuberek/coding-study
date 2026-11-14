def candy(ratings: list[int]) -> int:
    total = 1
    up = 0  # length of the current rising run: the latest child got up + 1 candies
    down = 0  # length of the current falling run
    peak = 0  # the rising run length at the top of the current peak
    for i in range(1, len(ratings)):
        if ratings[i] > ratings[i - 1]:
            up += 1
            peak = up
            down = 0
            total += up + 1
        elif ratings[i] == ratings[i - 1]:
            up = down = peak = 0
            total += 1
        else:
            up = 0
            down += 1
            # Every child on the falling run gets one more candy; the peak only needs one
            # more once the falling run is longer than the rising run that built it.
            total += down + (1 if down > peak else 0)
    return total
