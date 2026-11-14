pub fn longest_palindrome(s: String) -> String {
    let bytes = s.as_bytes();
    let n = bytes.len();
    let (mut best_start, mut best_length) = (0, 1);
    // Center c sits on character c / 2 when c is even, between two characters when c is odd.
    for center in 0..2 * n - 1 {
        // bytes[left..right] is the palindrome found so far: one character for an even
        // center, none for an odd one. Keeping `left` one past the next character to
        // compare means it never drops below zero.
        let (mut left, mut right) = (center.div_ceil(2), center / 2 + 1);
        while left > 0 && right < n && bytes[left - 1] == bytes[right] {
            left -= 1;
            right += 1;
        }
        if right - left > best_length {
            best_start = left;
            best_length = right - left;
        }
    }
    s[best_start..best_start + best_length].to_string()
}
