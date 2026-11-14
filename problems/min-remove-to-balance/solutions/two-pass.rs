pub fn min_remove_to_make_valid(s: String) -> String {
    // Pass 1, left to right: drop every closer that finds nothing open.
    let mut kept: Vec<char> = Vec::with_capacity(s.len());
    let mut open_count = 0;
    for character in s.chars() {
        match character {
            ')' if open_count == 0 => continue,
            ')' => open_count -= 1,
            '(' => open_count += 1,
            _ => {}
        }
        kept.push(character);
    }
    // Pass 2, right to left: drop the last `open_count` openers, which are never closed.
    let mut result: Vec<char> = Vec::with_capacity(kept.len());
    for &character in kept.iter().rev() {
        if character == '(' && open_count > 0 {
            open_count -= 1;
            continue;
        }
        result.push(character);
    }
    result.iter().rev().collect()
}
