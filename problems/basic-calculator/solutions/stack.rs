pub fn calculate(s: String) -> i32 {
    // Signed terms; the last one may still be multiplied or divided.
    let mut terms: Vec<i32> = Vec::new();
    let mut number = 0;
    let mut operator = b'+'; // the operator in front of the number being read
    for (i, character) in s.bytes().enumerate() {
        if character.is_ascii_digit() {
            number = number * 10 + i32::from(character - b'0');
        }
        if matches!(character, b'+' | b'-' | b'*' | b'/') || i == s.len() - 1 {
            match operator {
                b'+' => terms.push(number),
                b'-' => terms.push(-number),
                b'*' => *terms.last_mut().unwrap() *= number,
                _ => *terms.last_mut().unwrap() /= number, // truncates toward zero
            }
            operator = character;
            number = 0;
        }
    }
    terms.iter().sum()
}
