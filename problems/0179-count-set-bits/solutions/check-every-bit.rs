const WORD_BITS: u32 = 32;

pub fn hamming_weight(n: i64) -> i32 {
    (0..WORD_BITS)
        .map(|position| ((n >> position) & 1) as i32)
        .sum()
}
