/// The letters of the digits '2' to '9', in that order.
const KEYPAD: [&str; 8] = ["abc", "def", "ghi", "jkl", "mno", "pqrs", "tuv", "wxyz"];

pub fn letter_combinations(digits: String) -> Vec<String> {
    if digits.is_empty() {
        return Vec::new();
    }
    let mut words = vec![String::new()];
    for digit in digits.bytes() {
        let letters = KEYPAD[usize::from(digit - b'2')];
        words = words
            .iter()
            .flat_map(|word| letters.chars().map(move |letter| format!("{word}{letter}")))
            .collect();
    }
    words
}
