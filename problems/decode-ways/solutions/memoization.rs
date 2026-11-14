const NOT_COMPUTED: i32 = -1;

/// The number of readings of the suffix `digits[start..]`.
fn ways_from(start: usize, digits: &[u8], memo: &mut [i32]) -> i32 {
    if start == digits.len() {
        return 1;
    }
    if digits[start] == b'0' {
        return 0;
    }
    if memo[start] == NOT_COMPUTED {
        let mut count = ways_from(start + 1, digits, memo);
        if start + 1 < digits.len() {
            let pair = (digits[start] - b'0') * 10 + (digits[start + 1] - b'0');
            if (10..=26).contains(&pair) {
                count += ways_from(start + 2, digits, memo);
            }
        }
        memo[start] = count;
    }
    memo[start]
}

pub fn num_decodings(s: String) -> i32 {
    let mut memo = vec![NOT_COMPUTED; s.len()];
    ways_from(0, s.as_bytes(), &mut memo)
}
