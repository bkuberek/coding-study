pub struct NumArray {
    nums: Vec<i32>,
}

impl NumArray {
    pub fn new(nums: Vec<i32>) -> Self {
        NumArray { nums }
    }

    pub fn update(&mut self, index: i32, value: i32) {
        self.nums[index as usize] = value;
    }

    pub fn sum_range(&mut self, left: i32, right: i32) -> i64 {
        self.nums[left as usize..=right as usize]
            .iter()
            .map(|&value| i64::from(value))
            .sum()
    }
}
