pub struct MedianFinder {
    values: Vec<i32>, // every number so far, ascending
}

impl MedianFinder {
    pub fn new() -> Self {
        MedianFinder { values: Vec::new() }
    }

    pub fn add_num(&mut self, num: i32) {
        // The binary search is O(log n); shifting the tail to open the slot is O(n).
        let position = self.values.partition_point(|&value| value < num);
        self.values.insert(position, num);
    }

    pub fn find_median(&mut self) -> f64 {
        let middle = self.values.len() / 2;
        if self.values.len() % 2 == 1 {
            return f64::from(self.values[middle]);
        }
        f64::from(self.values[middle - 1] + self.values[middle]) / 2.0
    }
}
