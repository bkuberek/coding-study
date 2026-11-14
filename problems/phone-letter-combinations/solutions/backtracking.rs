/// The letters of the digits '2' to '9', in that order.
const KEYPAD: [&str; 8] = ["abc", "def", "ghi", "jkl", "mno", "pqrs", "tuv", "wxyz"];

pub fn letter_combinations(digits: String) -> Vec<String> {
    if digits.is_empty() {
        return Vec::new();
    }
    let mut words = Vec::new();
    let mut letters = vec![' '; digits.len()];
    fill(digits.as_bytes(), 0, &mut letters, &mut words);
    words
}

fn fill(digits: &[u8], slot: usize, letters: &mut [char], words: &mut Vec<String>) {
    if slot == digits.len() {
        words.push(letters.iter().collect());
        return;
    }
    for letter in KEYPAD[usize::from(digits[slot] - b'2')].chars() {
        letters[slot] = letter;
        fill(digits, slot + 1, letters, words);
    }
}
