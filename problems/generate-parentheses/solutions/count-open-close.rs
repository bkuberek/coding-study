pub fn generate_parenthesis(n: i32) -> Vec<String> {
    let mut result = Vec::new();
    let mut brackets = String::with_capacity(2 * n as usize);
    extend(n, 0, 0, &mut brackets, &mut result);
    result
}

fn extend(n: i32, opened: i32, closed: i32, brackets: &mut String, result: &mut Vec<String>) {
    if closed == n {
        result.push(brackets.clone());
        return;
    }
    if opened < n {
        brackets.push('(');
        extend(n, opened + 1, closed, brackets, result);
        brackets.pop();
    }
    // A ")" is allowed only while it has an unmatched "(" to close.
    if closed < opened {
        brackets.push(')');
        extend(n, opened, closed + 1, brackets, result);
        brackets.pop();
    }
}
