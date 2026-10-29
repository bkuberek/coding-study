pub fn min_eating_speed(piles: Vec<i32>, h: i32) -> i32 {
    let h = i64::from(h);
    // Hours never increase with speed: find the first speed in [1, max(piles)] that fits.
    let mut low: i64 = 1;
    let mut high = i64::from(*piles.iter().max().unwrap());
    while low < high {
        let speed = low + (high - low) / 2;
        if hours_at(&piles, speed) <= h {
            high = speed;
        } else {
            low = speed + 1;
        }
    }
    low as i32
}

/// The total can reach 10^4 piles of 10^9 hours, so it is an `i64`.
fn hours_at(piles: &[i32], speed: i64) -> i64 {
    piles
        .iter()
        .map(|&pile| (i64::from(pile) + speed - 1) / speed) // ceiling division
        .sum()
}
