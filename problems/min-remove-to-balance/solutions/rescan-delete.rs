pub fn min_remove_to_make_valid(s: String) -> String {
    let mut text: Vec<char> = s.chars().collect();
    while let Some(position) = first_offender(&text) {
        text.remove(position); // shifts the rest of the text: O(n)
    }
    text.into_iter().collect()
}

/// A parenthesis that cannot be matched, or `None` when the text is balanced.
fn first_offender(text: &[char]) -> Option<usize> {
    let mut depth = 0;
    for (position, &character) in text.iter().enumerate() {
        match character {
            '(' => depth += 1,
            ')' => {
                if depth == 0 {
                    return Some(position); // a closer with nothing open before it
                }
                depth -= 1;
            }
            _ => {}
        }
    }
    if depth == 0 {
        return None;
    }
    // Some openers are never closed: the last opener with no closer left after it is one.
    let mut closers = 0;
    for (position, &character) in text.iter().enumerate().rev() {
        match character {
            ')' => closers += 1,
            '(' => {
                if closers == 0 {
                    return Some(position);
                }
                closers -= 1;
            }
            _ => {}
        }
    }
    None
}
