pub fn valid_palindrome(s: String) -> bool {
    let bytes = s.as_bytes();
    if is_palindrome(bytes) {
        return true;
    }
    (0..bytes.len()).any(|index| {
        let candidate = [&bytes[..index], &bytes[index + 1..]].concat();
        is_palindrome(&candidate)
    })
}

fn is_palindrome(bytes: &[u8]) -> bool {
    bytes.iter().eq(bytes.iter().rev())
}
