const USED: char = '#';
const STEPS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

pub fn find_words(mut board: Vec<Vec<char>>, words: Vec<String>) -> Vec<String> {
    words
        .into_iter()
        .filter(|word| {
            let letters: Vec<char> = word.chars().collect();
            on_board(&mut board, &letters)
        })
        .collect()
}

fn on_board(board: &mut [Vec<char>], word: &[char]) -> bool {
    for row in 0..board.len() {
        for col in 0..board[0].len() {
            if trace(board, word, (row, col), 0) {
                return true;
            }
        }
    }
    false
}

/// Can `word[position..]` be spelled starting at this cell?
fn trace(board: &mut [Vec<char>], word: &[char], cell: (usize, usize), position: usize) -> bool {
    let (row, col) = cell;
    if board[row][col] != word[position] {
        return false;
    }
    if position + 1 == word.len() {
        return true;
    }
    board[row][col] = USED;
    let found = STEPS.iter().any(|&step| {
        neighbor(board, cell, step).is_some_and(|next| trace(board, word, next, position + 1))
    });
    board[row][col] = word[position];
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
