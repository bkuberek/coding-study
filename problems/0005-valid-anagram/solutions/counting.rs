const ALPHABET_SIZE: usize = 26;

pub fn is_anagram(s: String, t: String) -> bool {
    if s.len() != t.len() {
        return false;
    }
    let mut counts = [0i32; ALPHABET_SIZE];
    for letter in s.bytes() {
        counts[usize::from(letter - b'a')] += 1;
    }
    for letter in t.bytes() {
        let count = &mut counts[usize::from(letter - b'a')];
        *count -= 1;
        if *count < 0 {
            return false;
        }
    }
    true
}
