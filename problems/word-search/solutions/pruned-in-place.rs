const STEPS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];
const USED: char = '#';

pub fn exist(mut board: Vec<Vec<char>>, word: String) -> bool {
    let mut available = [0usize; 26];
    for &letter in board.iter().flatten() {
        available[slot(letter)] += 1;
    }
    let mut letters: Vec<char> = word.chars().collect();
    let mut needed = [0usize; 26];
    for &letter in &letters {
        needed[slot(letter)] += 1;
    }
    if available
        .iter()
        .zip(&needed)
        .any(|(have, need)| have < need)
    {
        return false;
    }
    // A walk read backwards is also a walk: start from whichever end is rarer on the board.
    if available[slot(letters[0])] > available[slot(letters[letters.len() - 1])] {
        letters.reverse();
    }
    for r in 0..board.len() {
        for c in 0..board[0].len() {
            if spells_from(&mut board, &letters, (r, c), 0) {
                return true;
            }
        }
    }
    false
}

fn spells_from(board: &mut [Vec<char>], letters: &[char], cell: (usize, usize), k: usize) -> bool {
    let (r, c) = cell;
    if board[r][c] != letters[k] {
        return false;
    }
    if k + 1 == letters.len() {
        return true;
    }
    board[r][c] = USED;
    let found = STEPS.iter().any(|&step| {
        neighbor(board, cell, step).is_some_and(|next| spells_from(board, letters, next, k + 1))
    });
    board[r][c] = letters[k];
    found
}

/// The cell one `step` away, or `None` when it falls off the board.
fn neighbor(
    board: &[Vec<char>],
    cell: (usize, usize),
    step: (isize, isize),
) -> Option<(usize, usize)> {
    let row = cell.0.checked_add_signed(step.0)?;
    let col = cell.1.checked_add_signed(step.1)?;
    (row < board.len() && col < board[0].len()).then_some((row, col))
}

fn slot(letter: char) -> usize {
    usize::from(letter as u8 - b'a')
}
