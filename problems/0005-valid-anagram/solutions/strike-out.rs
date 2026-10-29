pub fn is_anagram(s: String, t: String) -> bool {
    if s.len() != t.len() {
        return false;
    }
    let mut remaining = t.into_bytes();
    for letter in s.bytes() {
        let Some(position) = remaining.iter().position(|&slot| slot == letter) else {
            return false;
        };
        // A struck-out slot holds zero, which is never a lowercase letter.
        remaining[position] = 0;
    }
    true
}
