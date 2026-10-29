pub fn calculate(s: String) -> i32 {
    let mut total = 0; // the sum of the finished terms
    let mut term = 0; // the signed term still being built
    let mut number = 0;
    let mut operator = b'+'; // the operator in front of the number being read
    for (i, character) in s.bytes().enumerate() {
        if character.is_ascii_digit() {
            number = number * 10 + i32::from(character - b'0');
        }
        if matches!(character, b'+' | b'-' | b'*' | b'/') || i == s.len() - 1 {
            match operator {
                b'+' | b'-' => {
                    total += term;
                    term = if operator == b'+' { number } else { -number };
                }
                b'*' => term *= number,
                _ => term /= number, // truncates toward zero
            }
            operator = character;
            number = 0;
        }
    }
    total + term
}
