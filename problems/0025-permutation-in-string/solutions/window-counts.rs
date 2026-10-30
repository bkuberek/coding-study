const ALPHABET_SIZE: usize = 26;

pub fn check_inclusion(pattern: String, text: String) -> bool {
    let (pattern, text) = (pattern.as_bytes(), text.as_bytes());
    let width = pattern.len();
    if width > text.len() {
        return false;
    }
    let mut need = [0usize; ALPHABET_SIZE];
    let mut window = [0usize; ALPHABET_SIZE];
    for &byte in pattern {
        need[usize::from(byte - b'a')] += 1;
    }
    for (right, &byte) in text.iter().enumerate() {
        window[usize::from(byte - b'a')] += 1;
        if right >= width {
            window[usize::from(text[right - width] - b'a')] -= 1;
        }
        if right + 1 >= width && window == need {
            return true;
        }
    }
    false
}
