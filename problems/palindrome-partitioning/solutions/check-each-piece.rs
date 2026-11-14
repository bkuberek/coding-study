pub fn partition(s: String) -> Vec<Vec<String>> {
    let mut result = Vec::new();
    cut_from(&s, 0, &mut Vec::new(), &mut result);
    result
}

fn is_palindrome(text: &[u8], mut left: usize, mut right: usize) -> bool {
    while left < right {
        if text[left] != text[right] {
            return false;
        }
        left += 1;
        right -= 1;
    }
    true
}

fn cut_from(s: &str, start: usize, pieces: &mut Vec<String>, result: &mut Vec<Vec<String>>) {
    if start == s.len() {
        result.push(pieces.clone());
        return;
    }
    for end in start..s.len() {
        if is_palindrome(s.as_bytes(), start, end) {
            pieces.push(s[start..=end].to_string());
            cut_from(s, end + 1, pieces, result);
            pieces.pop();
        }
    }
}
