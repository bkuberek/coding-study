pub fn count_bits(n: i32) -> Vec<i32> {
    let n = n as usize;
    let mut bits = vec![0; n + 1];
    for i in 1..=n {
        // i >> 1 drops the lowest bit of i and is smaller than i, so its count is known.
        bits[i] = bits[i >> 1] + (i & 1) as i32;
    }
    bits
}
