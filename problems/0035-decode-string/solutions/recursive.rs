pub fn decode_string(s: String) -> String {
    decode_group(s.as_bytes(), 0).0
}

/// Decodes from `position` up to the `]` that closes the current group, or to the end of `s`.
/// Returns the decoded text and the position just after that `]`.
fn decode_group(s: &[u8], mut position: usize) -> (String, usize) {
    let mut decoded = String::new();
    let mut count = 0;
    while position < s.len() {
        let character = s[position];
        position += 1;
        match character {
            b'0'..=b'9' => count = count * 10 + usize::from(character - b'0'),
            b'[' => {
                let (inner, next) = decode_group(s, position);
                decoded.push_str(&inner.repeat(count));
                position = next;
                count = 0;
            }
            b']' => break,
            _ => decoded.push(char::from(character)),
        }
    }
    (decoded, position)
}
