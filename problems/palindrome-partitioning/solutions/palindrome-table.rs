pub fn partition(s: String) -> Vec<Vec<String>> {
    let text = s.as_bytes();
    let n = text.len();
    // palindrome[i][j]: whether s[i..=j] reads the same both ways. Row i depends on row i + 1.
    let mut palindrome = vec![vec![false; n]; n];
    for i in (0..n).rev() {
        for j in i..n {
            palindrome[i][j] = text[i] == text[j] && (j - i < 2 || palindrome[i + 1][j - 1]);
        }
    }

    let mut result = Vec::new();
    cut_from(&s, &palindrome, 0, &mut Vec::new(), &mut result);
    result
}

fn cut_from(
    s: &str,
    palindrome: &[Vec<bool>],
    start: usize,
    pieces: &mut Vec<String>,
    result: &mut Vec<Vec<String>>,
) {
    if start == s.len() {
        result.push(pieces.clone());
        return;
    }
    for end in start..s.len() {
        if palindrome[start][end] {
            pieces.push(s[start..=end].to_string());
            cut_from(s, palindrome, end + 1, pieces, result);
            pieces.pop();
        }
    }
}
