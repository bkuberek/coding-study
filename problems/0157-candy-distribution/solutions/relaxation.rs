pub fn candy(ratings: Vec<i32>) -> i32 {
    let n = ratings.len();
    let mut candies = vec![1; n];
    let mut changed = true;
    while changed {
        // Raise any child who does not have more than a lower-rated neighbor; repeat until no
        // rule is violated. Counts only grow, and each raise is the least that fixes it.
        changed = false;
        for i in 0..n {
            if i > 0 && ratings[i] > ratings[i - 1] && candies[i] <= candies[i - 1] {
                candies[i] = candies[i - 1] + 1;
                changed = true;
            }
            if i + 1 < n && ratings[i] > ratings[i + 1] && candies[i] <= candies[i + 1] {
                candies[i] = candies[i + 1] + 1;
                changed = true;
            }
        }
    }
    candies.iter().sum()
}
