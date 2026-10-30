pub fn count_bits(n: i32) -> Vec<i32> {
    (0..=n)
        .map(|i| {
            let mut count = 0;
            let mut word = i;
            while word != 0 {
                word &= word - 1; // each step clears the lowest set bit
                count += 1;
            }
            count
        })
        .collect()
}
