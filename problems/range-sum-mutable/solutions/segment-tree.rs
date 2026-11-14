pub struct NumArray {
    size: usize,
    // Leaves at size .. 2 * size - 1; node i holds the sum of its children 2i and 2i + 1.
    tree: Vec<i64>,
}

impl NumArray {
    pub fn new(nums: Vec<i32>) -> Self {
        let size = nums.len();
        let mut tree = vec![0_i64; 2 * size];
        for (i, &value) in nums.iter().enumerate() {
            tree[size + i] = i64::from(value);
        }
        for node in (1..size).rev() {
            tree[node] = tree[2 * node] + tree[2 * node + 1];
        }
        NumArray { size, tree }
    }

    pub fn update(&mut self, index: i32, value: i32) {
        let mut node = index as usize + self.size;
        self.tree[node] = i64::from(value);
        while node > 1 {
            node >>= 1;
            self.tree[node] = self.tree[2 * node] + self.tree[2 * node + 1];
        }
    }

    pub fn sum_range(&mut self, left: i32, right: i32) -> i64 {
        let mut total = 0;
        // Half-open [low, high) over the leaves, narrowed one level per round.
        let mut low = left as usize + self.size;
        let mut high = right as usize + self.size + 1;
        while low < high {
            if low & 1 == 1 {
                total += self.tree[low];
                low += 1;
            }
            if high & 1 == 1 {
                high -= 1;
                total += self.tree[high];
            }
            low >>= 1;
            high >>= 1;
        }
        total
    }
}
