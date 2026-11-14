pub struct NumArray {
    nums: Vec<i32>,
}

impl NumArray {
    pub fn new(nums: Vec<i32>) -> Self {
        NumArray { nums }
    }

    pub fn sum_range(&mut self, left: i32, right: i32) -> i64 {
        self.nums[left as usize..=right as usize]
            .iter()
            .map(|&value| i64::from(value))
            .sum()
    }
}
