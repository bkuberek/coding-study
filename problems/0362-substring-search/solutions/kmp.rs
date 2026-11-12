pub fn find_all_occurrences(text: String, pattern: String) -> Vec<i32> {
    let (text, pattern) = (text.as_bytes(), pattern.as_bytes());
    let border = border_table(pattern);
    let mut found = Vec::new();
    let mut matched = 0;
    for (position, &letter) in text.iter().enumerate() {
        while matched > 0 && letter != pattern[matched] {
            matched = border[matched - 1];
        }
        if letter == pattern[matched] {
            matched += 1;
        }
        if matched == pattern.len() {
            found.push((position + 1 - pattern.len()) as i32);
            matched = border[matched - 1];
        }
    }
    found
}

// border[i] is the length of the longest proper prefix of pattern[..=i] that is also a suffix of it.
fn border_table(pattern: &[u8]) -> Vec<usize> {
    let mut border = vec![0; pattern.len()];
    let mut length = 0;
    for i in 1..pattern.len() {
        while length > 0 && pattern[i] != pattern[length] {
            length = border[length - 1];
        }
        if pattern[i] == pattern[length] {
            length += 1;
        }
        border[i] = length;
    }
    border
}
