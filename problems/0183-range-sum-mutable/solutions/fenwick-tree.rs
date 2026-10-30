/// The lowest set bit of `i`. `usize` has no unary minus, so `-i` is spelled `wrapping_neg`.
fn low_bit(i: usize) -> usize {
    i & i.wrapping_neg()
}

pub struct NumArray {
    values: Vec<i32>,
    // tree[i] (1-based) holds the sum of the low_bit(i) values ending at position i - 1.
    tree: Vec<i64>,
}

impl NumArray {
    pub fn new(nums: Vec<i32>) -> Self {
        let size = nums.len();
        let mut tree = vec![0_i64; size + 1];
        for i in 1..=size {
            tree[i] += i64::from(nums[i - 1]);
            let parent = i + low_bit(i);
            if parent <= size {
                tree[parent] += tree[i];
            }
        }
        NumArray { values: nums, tree }
    }

    pub fn update(&mut self, index: i32, value: i32) {
        let index = index as usize;
        let delta = i64::from(value) - i64::from(self.values[index]);
        self.values[index] = value;
        let mut i = index + 1;
        while i < self.tree.len() {
            self.tree[i] += delta;
            i += low_bit(i);
        }
    }

    pub fn sum_range(&mut self, left: i32, right: i32) -> i64 {
        self.prefix(right as usize + 1) - self.prefix(left as usize)
    }

    /// Sum of the first `count` values.
    fn prefix(&self, count: usize) -> i64 {
        let mut total = 0;
        let mut i = count;
        while i > 0 {
            total += self.tree[i];
            i -= low_bit(i);
        }
        total
    }
}
