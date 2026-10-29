pub fn is_valid(s: String) -> bool {
    let mut open_brackets: Vec<char> = Vec::new();
    for character in s.chars() {
        match character {
            '(' | '[' | '{' => open_brackets.push(character),
            _ => {
                if open_brackets.pop() != Some(opener_of(character)) {
                    return false;
                }
            }
        }
    }
    open_brackets.is_empty()
}

fn opener_of(closer: char) -> char {
    match closer {
        ')' => '(',
        ']' => '[',
        _ => '{',
    }
}
