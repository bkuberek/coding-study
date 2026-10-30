use std::cmp::Reverse;
use std::collections::BinaryHeap;

pub struct MedianFinder {
    /// The smaller half as a max-heap.
    low: BinaryHeap<i32>,
    /// The larger half as a min-heap. `low` holds as many values as `high`, or one more.
    high: BinaryHeap<Reverse<i32>>,
}

impl MedianFinder {
    pub fn new() -> Self {
        MedianFinder {
            low: BinaryHeap::new(),
            high: BinaryHeap::new(),
        }
    }

    pub fn add_num(&mut self, num: i32) {
        // Route the number through `low` so that every value in `low` stays <= every value in
        // `high`.
        self.low.push(num);
        if let Some(largest) = self.low.pop() {
            self.high.push(Reverse(largest));
        }
        if self.high.len() > self.low.len() {
            if let Some(Reverse(smallest)) = self.high.pop() {
                self.low.push(smallest);
            }
        }
    }

    pub fn find_median(&mut self) -> f64 {
        let low_top = *self.low.peek().expect("findMedian follows an addNum");
        if self.low.len() > self.high.len() {
            return f64::from(low_top);
        }
        let Reverse(high_top) = *self.high.peek().expect("both halves hold a value");
        f64::from(low_top + high_top) / 2.0
    }
}
