/// Whether the suffix `s[start..]` can be split into dictionary words.
fn can_split_from(start: usize, s: &str, word_dict: &[String], memo: &mut [Option<bool>]) -> bool {
    if start == s.len() {
        return true;
    }
    if let Some(known) = memo[start] {
        return known;
    }
    let answer = word_dict.iter().any(|word| {
        s[start..].starts_with(word.as_str())
            && can_split_from(start + word.len(), s, word_dict, memo)
    });
    memo[start] = Some(answer);
    answer
}

pub fn word_break(s: String, word_dict: Vec<String>) -> bool {
    let mut memo = vec![None; s.len()];
    can_split_from(0, &s, &word_dict, &mut memo)
}
