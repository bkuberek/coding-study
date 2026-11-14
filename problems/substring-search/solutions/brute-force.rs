pub fn find_all_occurrences(text: String, pattern: String) -> Vec<i32> {
    let (text, pattern) = (text.as_bytes(), pattern.as_bytes());
    let mut found = Vec::new();
    for start in 0..(text.len() + 1).saturating_sub(pattern.len()) {
        let mut offset = 0;
        while offset < pattern.len() && text[start + offset] == pattern[offset] {
            offset += 1;
        }
        if offset == pattern.len() {
            found.push(start as i32);
        }
    }
    found
}
