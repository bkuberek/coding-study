const SIDE: usize = 9;
const BOX: usize = 3;
const EMPTY: char = '.';

pub fn is_valid_sudoku(board: Vec<Vec<char>>) -> bool {
    for row in 0..SIDE {
        for column in 0..SIDE {
            let digit = board[row][column];
            if digit != EMPTY && repeats(&board, row, column, digit) {
                return false;
            }
        }
    }
    true
}

/// Whether another cell in the same row, column or box holds `digit`.
fn repeats(board: &[Vec<char>], row: usize, column: usize, digit: char) -> bool {
    let (top, left) = (row - row % BOX, column - column % BOX);
    for i in 0..SIDE {
        if i != column && board[row][i] == digit {
            return true;
        }
        if i != row && board[i][column] == digit {
            return true;
        }
        let (box_row, box_column) = (top + i / BOX, left + i % BOX);
        if (box_row, box_column) != (row, column) && board[box_row][box_column] == digit {
            return true;
        }
    }
    false
}
