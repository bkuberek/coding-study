use std::collections::HashSet;

pub fn word_break(s: String, word_dict: Vec<String>) -> bool {
    let words: HashSet<&str> = word_dict.iter().map(String::as_str).collect();
    let longest = word_dict.iter().map(String::len).max().unwrap_or(0);
    // ok[i] is true when the prefix s[..i] can be split into dictionary words.
    let mut ok = vec![false; s.len() + 1];
    ok[0] = true;
    for end in 1..=s.len() {
        for start in end.saturating_sub(longest)..end {
            if ok[start] && words.contains(&s[start..end]) {
                ok[end] = true;
                break;
            }
        }
    }
    ok[s.len()]
}
