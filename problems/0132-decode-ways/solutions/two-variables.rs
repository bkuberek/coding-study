pub fn num_decodings(s: String) -> i32 {
    let digits = s.as_bytes();
    // Before digit i: one_back counts readings of s[..i] and two_back those of s[..i - 1].
    let (mut two_back, mut one_back) = (0, 1);
    for (i, &digit) in digits.iter().enumerate() {
        let mut current = if digit != b'0' { one_back } else { 0 };
        if i > 0 {
            let pair = (digits[i - 1] - b'0') * 10 + (digit - b'0');
            if (10..=26).contains(&pair) {
                current += two_back;
            }
        }
        (two_back, one_back) = (one_back, current);
    }
    one_back
}
