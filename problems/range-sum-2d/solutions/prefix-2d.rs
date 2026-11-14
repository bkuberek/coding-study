pub struct NumMatrix {
    prefix: Vec<Vec<i32>>,
}

impl NumMatrix {
    pub fn new(matrix: Vec<Vec<i32>>) -> Self {
        let cols = matrix[0].len();
        // prefix[r][c] is the sum of the sub-grid matrix[..r][..c]; row 0 and column 0 are zeros.
        let mut prefix = vec![vec![0; cols + 1]];
        for cells in &matrix {
            let above = &prefix[prefix.len() - 1];
            let mut row = vec![0; cols + 1];
            let mut running = 0;
            for (c, &value) in cells.iter().enumerate() {
                running += value;
                row[c + 1] = above[c + 1] + running;
            }
            prefix.push(row);
        }
        NumMatrix { prefix }
    }

    pub fn sum_region(&mut self, row1: i32, col1: i32, row2: i32, col2: i32) -> i32 {
        let (row1, col1, row2, col2) = (row1 as usize, col1 as usize, row2 as usize, col2 as usize);
        let p = &self.prefix;
        p[row2 + 1][col2 + 1] - p[row1][col2 + 1] - p[row2 + 1][col1] + p[row1][col1]
    }
}
