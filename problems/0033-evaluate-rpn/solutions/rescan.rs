/// One entry of the expression: a number, or an operator borrowed from the tokens.
enum Item<'a> {
    Number(i32),
    Operator(&'a str),
}

pub fn eval_rpn(tokens: Vec<String>) -> i32 {
    // Operators stay as strings; numbers are parsed once.
    let mut items: Vec<Item> = tokens
        .iter()
        .map(|token| match token.as_str() {
            "+" | "-" | "*" | "/" => Item::Operator(token),
            number => Item::Number(number.parse().unwrap()),
        })
        .collect();
    while items.len() > 1 {
        // The leftmost operator always has its two operands directly in front of it.
        let position = items
            .iter()
            .position(|item| matches!(item, Item::Operator(_)))
            .unwrap();
        let result = match (&items[position - 2], &items[position - 1], &items[position]) {
            (Item::Number(left), Item::Number(right), Item::Operator(operator)) => {
                apply(operator, *left, *right)
            }
            _ => unreachable!("an operator follows two numbers"),
        };
        items.splice(position - 2..=position, [Item::Number(result)]);
    }
    match items[0] {
        Item::Number(value) => value,
        Item::Operator(_) => unreachable!("one number is left"),
    }
}

fn apply(operator: &str, left: i32, right: i32) -> i32 {
    match operator {
        "+" => left + right,
        "-" => left - right,
        "*" => left * right,
        _ => left / right, // truncates toward zero
    }
}
