def candy(ratings: list[int]) -> int:
    n = len(ratings)
    candies = [1] * n
    changed = True
    while changed:
        # Raise any child who does not have more than a lower-rated neighbor; repeat until no
        # rule is violated. Counts only grow, and each raise is the least that fixes it.
        changed = False
        for i in range(n):
            if i > 0 and ratings[i] > ratings[i - 1] and candies[i] <= candies[i - 1]:
                candies[i] = candies[i - 1] + 1
                changed = True
            if i < n - 1 and ratings[i] > ratings[i + 1] and candies[i] <= candies[i + 1]:
                candies[i] = candies[i + 1] + 1
                changed = True
    return sum(candies)
