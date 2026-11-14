pub fn min_eating_speed(piles: Vec<i32>, h: i32) -> i32 {
    let h = i64::from(h);
    let mut speed: i64 = 1;
    while hours_at(&piles, speed) > h {
        speed += 1;
    }
    speed as i32
}

/// The total can reach 10^4 piles of 10^9 hours, so it is an `i64`.
fn hours_at(piles: &[i32], speed: i64) -> i64 {
    piles
        .iter()
        .map(|&pile| (i64::from(pile) + speed - 1) / speed) // ceiling division
        .sum()
}
