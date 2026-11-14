pub fn min_remove_to_make_valid(s: String) -> String {
    let mut deleted = vec![false; s.len()];
    let mut open_positions: Vec<usize> = Vec::new();
    for (position, character) in s.chars().enumerate() {
        match character {
            '(' => open_positions.push(position),
            ')' => {
                // Matches the most recent unmatched opener, or can never match.
                if open_positions.pop().is_none() {
                    deleted[position] = true;
                }
            }
            _ => {}
        }
    }
    for position in open_positions {
        deleted[position] = true; // openers that were never closed
    }
    s.chars()
        .zip(deleted)
        .filter(|&(_, is_deleted)| !is_deleted)
        .map(|(character, _)| character)
        .collect()
}
