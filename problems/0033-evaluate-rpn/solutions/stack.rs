pub fn eval_rpn(tokens: Vec<String>) -> i32 {
    let mut operands: Vec<i32> = Vec::new();
    for token in &tokens {
        match token.as_str() {
            "+" | "-" | "*" | "/" => {
                let right = operands.pop().unwrap();
                let left = operands.pop().unwrap();
                operands.push(apply(token, left, right));
            }
            number => operands.push(number.parse().unwrap()),
        }
    }
    operands[0]
}

fn apply(operator: &str, left: i32, right: i32) -> i32 {
    match operator {
        "+" => left + right,
        "-" => left - right,
        "*" => left * right,
        _ => left / right, // truncates toward zero
    }
}
