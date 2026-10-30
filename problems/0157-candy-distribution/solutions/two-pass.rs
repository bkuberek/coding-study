pub fn candy(ratings: Vec<i32>) -> i32 {
    let n = ratings.len();
    let mut candies = vec![1; n];
    // Left to right: the fewest candies that respect every left neighbor.
    for i in 1..n {
        if ratings[i] > ratings[i - 1] {
            candies[i] = candies[i - 1] + 1;
        }
    }
    // Right to left: also respect every right neighbor, without undoing the first pass.
    // Every index before the last one; empty for a single child.
    for i in (0..n - 1).rev() {
        if ratings[i] > ratings[i + 1] {
            candies[i] = candies[i].max(candies[i + 1] + 1);
        }
    }
    candies.iter().sum()
}
