/// The operators of each precedence level, tightest first.
const LEVELS: [&[u8]; 2] = [b"*/", b"+-"];

pub fn calculate(s: String) -> i32 {
    let (mut values, mut operators) = tokenize(&s);
    for level in LEVELS {
        while let Some(position) = operators
            .iter()
            .position(|operator| level.contains(operator))
        {
            values[position] = apply(operators[position], values[position], values[position + 1]);
            values.remove(position + 1);
            operators.remove(position);
        }
    }
    values[0]
}

/// Splits `s` into numbers and operators; `operators[i]` joins `values[i]` and `values[i + 1]`.
fn tokenize(s: &str) -> (Vec<i32>, Vec<u8>) {
    let mut values = Vec::new();
    let mut operators = Vec::new();
    let mut number = 0;
    for character in s.bytes() {
        match character {
            b'0'..=b'9' => number = number * 10 + i32::from(character - b'0'),
            b'+' | b'-' | b'*' | b'/' => {
                values.push(number);
                operators.push(character);
                number = 0;
            }
            _ => {}
        }
    }
    values.push(number);
    (values, operators)
}

fn apply(operator: u8, left: i32, right: i32) -> i32 {
    match operator {
        b'+' => left + right,
        b'-' => left - right,
        b'*' => left * right,
        _ => left / right, // truncates toward zero
    }
}
