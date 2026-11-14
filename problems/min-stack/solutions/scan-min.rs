pub struct MinStack {
    values: Vec<i32>,
}

impl MinStack {
    pub fn new() -> Self {
        MinStack { values: Vec::new() }
    }

    pub fn push(&mut self, value: i32) {
        self.values.push(value);
    }

    pub fn pop(&mut self) {
        self.values.pop();
    }

    pub fn top(&mut self) -> i32 {
        self.values[self.values.len() - 1]
    }

    pub fn get_min(&mut self) -> i32 {
        // `min` scans every value: O(n) per call.
        *self.values.iter().min().unwrap()
    }
}
