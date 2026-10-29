pub fn is_palindrome(s: String) -> bool {
    let bytes = s.as_bytes();
    // `right` is one past the next byte to read, so it never underflows on an empty string.
    let (mut left, mut right) = (0, bytes.len());
    while left + 1 < right {
        let (first, last) = (bytes[left], bytes[right - 1]);
        if !first.is_ascii_alphanumeric() {
            left += 1;
        } else if !last.is_ascii_alphanumeric() {
            right -= 1;
        } else if !first.eq_ignore_ascii_case(&last) {
            return false;
        } else {
            left += 1;
            right -= 1;
        }
    }
    true
}
