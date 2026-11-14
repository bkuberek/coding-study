pub struct KthLargestTracker {
    k: usize,
    values: Vec<i32>, // every number so far, ascending
}

impl KthLargestTracker {
    pub fn new(k: i32, nums: Vec<i32>) -> Self {
        let mut values = nums;
        values.sort_unstable();
        KthLargestTracker { k: k as usize, values }
    }

    pub fn add(&mut self, value: i32) -> i32 {
        // The binary search is O(log n); shifting the tail to open the slot is O(n).
        let position = self.values.partition_point(|&existing| existing < value);
        self.values.insert(position, value);
        // The kth largest is the kth entry from the end.
        self.values[self.values.len() - self.k]
    }
}
