const STEPS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

pub fn exist(board: Vec<Vec<char>>, word: String) -> bool {
    let letters: Vec<char> = word.chars().collect();
    let mut visited = vec![vec![false; board[0].len()]; board.len()];
    for r in 0..board.len() {
        for c in 0..board[0].len() {
            if spells_from(&board, &letters, &mut visited, (r, c), 0) {
                return true;
            }
        }
    }
    false
}

/// Whether `letters[k..]` can be spelled by a walk that starts at `cell`.
fn spells_from(
    board: &[Vec<char>],
    letters: &[char],
    visited: &mut [Vec<bool>],
    cell: (usize, usize),
    k: usize,
) -> bool {
    let (r, c) = cell;
    if visited[r][c] || board[r][c] != letters[k] {
        return false;
    }
    if k + 1 == letters.len() {
        return true;
    }
    visited[r][c] = true;
    let found = STEPS.iter().any(|&step| {
        neighbor(board, cell, step)
            .is_some_and(|next| spells_from(board, letters, visited, next, k + 1))
    });
    visited[r][c] = false;
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
