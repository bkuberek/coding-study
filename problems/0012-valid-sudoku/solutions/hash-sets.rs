use std::collections::HashSet;

const SIDE: usize = 9;
const BOX: usize = 3;
const EMPTY: char = '.';

pub fn is_valid_sudoku(board: Vec<Vec<char>>) -> bool {
    let mut rows = vec![HashSet::new(); SIDE];
    let mut columns = vec![HashSet::new(); SIDE];
    let mut boxes = vec![HashSet::new(); SIDE];
    for row in 0..SIDE {
        for column in 0..SIDE {
            let digit = board[row][column];
            if digit == EMPTY {
                continue;
            }
            let box_index = (row / BOX) * BOX + column / BOX;
            // `insert` returns false for a digit already in the set, so one call checks and adds.
            if !rows[row].insert(digit)
                || !columns[column].insert(digit)
                || !boxes[box_index].insert(digit)
            {
                return false;
            }
        }
    }
    true
}
