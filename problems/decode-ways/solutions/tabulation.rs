pub fn num_decodings(s: String) -> i32 {
    let digits = s.as_bytes();
    // ways[i] is the number of readings of the prefix s[..i]; the empty prefix has one.
    let mut ways = vec![0; digits.len() + 1];
    ways[0] = 1;
    for i in 1..=digits.len() {
        if digits[i - 1] != b'0' {
            ways[i] += ways[i - 1];
        }
        if i >= 2 {
            let pair = (digits[i - 2] - b'0') * 10 + (digits[i - 1] - b'0');
            if (10..=26).contains(&pair) {
                ways[i] += ways[i - 2];
            }
        }
    }
    ways[digits.len()]
}
