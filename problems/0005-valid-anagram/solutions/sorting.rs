pub fn is_anagram(s: String, t: String) -> bool {
    if s.len() != t.len() {
        return false;
    }
    let (mut left, mut right) = (s.into_bytes(), t.into_bytes());
    left.sort_unstable();
    right.sort_unstable();
    left == right
}
