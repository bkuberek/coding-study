pub struct NumArray {
    prefix: Vec<i64>,
}

impl NumArray {
    pub fn new(nums: Vec<i32>) -> Self {
        // prefix[i] is the sum of nums[..i]; the leading 0 makes ranges that start at 0 uniform.
        let mut prefix = Vec::with_capacity(nums.len() + 1);
        prefix.push(0);
        let mut running = 0_i64;
        for value in nums {
            running += i64::from(value);
            prefix.push(running);
        }
        NumArray { prefix }
    }

    pub fn sum_range(&mut self, left: i32, right: i32) -> i64 {
        self.prefix[right as usize + 1] - self.prefix[left as usize]
    }
}
