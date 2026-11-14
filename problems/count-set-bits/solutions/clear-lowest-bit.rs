pub fn hamming_weight(n: i64) -> i32 {
    // The low 32 bits as an unsigned word: the input is below 2^32, so nothing is lost.
    let mut word = n as u32;
    let mut count = 0;
    while word != 0 {
        word &= word - 1; // clears the lowest set bit
        count += 1;
    }
    count
}
