pub struct NumMatrix {
    matrix: Vec<Vec<i32>>,
}

impl NumMatrix {
    pub fn new(matrix: Vec<Vec<i32>>) -> Self {
        NumMatrix { matrix }
    }

    pub fn sum_region(&mut self, row1: i32, col1: i32, row2: i32, col2: i32) -> i32 {
        let columns = col1 as usize..=col2 as usize;
        self.matrix[row1 as usize..=row2 as usize]
            .iter()
            .map(|cells| cells[columns.clone()].iter().sum::<i32>())
            .sum()
    }
}
