use std::cmp::Reverse;
use std::collections::BinaryHeap;

pub struct KthLargestTracker {
    k: usize,
    /// The k largest numbers seen so far. `BinaryHeap` is a max-heap, so wrapping each number in
    /// `Reverse` puts the smallest of them on top.
    top: BinaryHeap<Reverse<i32>>,
}

impl KthLargestTracker {
    pub fn new(k: i32, nums: Vec<i32>) -> Self {
        let mut tracker = KthLargestTracker {
            k: k as usize,
            top: BinaryHeap::new(),
        };
        for value in nums {
            tracker.offer(value);
        }
        tracker
    }

    pub fn add(&mut self, value: i32) -> i32 {
        self.offer(value);
        // Every add leaves at least k numbers, so the heap is full and has a top.
        let Reverse(smallest) = *self.top.peek().expect("the heap holds k numbers");
        smallest
    }

    fn offer(&mut self, value: i32) {
        self.top.push(Reverse(value));
        if self.top.len() > self.k {
            // k + 1 numbers are in the heap; the smallest cannot be among the k largest.
            self.top.pop();
        }
    }
}
