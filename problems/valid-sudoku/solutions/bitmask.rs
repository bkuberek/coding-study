const SIDE: usize = 9;
const BOX: usize = 3;
const EMPTY: char = '.';

pub fn is_valid_sudoku(board: Vec<Vec<char>>) -> bool {
    // Bit d - 1 of a mask is set once digit d has been seen in that row, column or box.
    let mut rows = [0u16; SIDE];
    let mut columns = [0u16; SIDE];
    let mut boxes = [0u16; SIDE];
    for row in 0..SIDE {
        for column in 0..SIDE {
            let digit = board[row][column];
            if digit == EMPTY {
                continue;
            }
            let bit = 1u16 << (digit.to_digit(10).expect("a digit from 1 to 9") - 1);
            let box_index = (row / BOX) * BOX + column / BOX;
            if (rows[row] | columns[column] | boxes[box_index]) & bit != 0 {
                return false;
            }
            rows[row] |= bit;
            columns[column] |= bit;
            boxes[box_index] |= bit;
        }
    }
    true
}
