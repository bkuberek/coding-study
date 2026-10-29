pub fn valid_palindrome(s: String) -> bool {
    let bytes = s.as_bytes();
    // `right` is one past the next byte to read, so it never underflows on an empty string.
    let (mut left, mut right) = (0, bytes.len());
    while left + 1 < right {
        if bytes[left] != bytes[right - 1] {
            return is_palindrome(&bytes[left + 1..right])
                || is_palindrome(&bytes[left..right - 1]);
        }
        left += 1;
        right -= 1;
    }
    true
}

fn is_palindrome(bytes: &[u8]) -> bool {
    let (mut left, mut right) = (0, bytes.len());
    while left + 1 < right {
        if bytes[left] != bytes[right - 1] {
            return false;
        }
        left += 1;
        right -= 1;
    }
    true
}
