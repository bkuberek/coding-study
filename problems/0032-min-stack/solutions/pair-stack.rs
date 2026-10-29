pub struct MinStack {
    /// `(value, minimum of this value and everything below it)`.
    entries: Vec<(i32, i32)>,
}

impl MinStack {
    pub fn new() -> Self {
        MinStack {
            entries: Vec::new(),
        }
    }

    pub fn push(&mut self, value: i32) {
        let minimum = self
            .entries
            .last()
            .map_or(value, |&(_, below)| value.min(below));
        self.entries.push((value, minimum));
    }

    pub fn pop(&mut self) {
        self.entries.pop();
    }

    pub fn top(&mut self) -> i32 {
        self.entries[self.entries.len() - 1].0
    }

    pub fn get_min(&mut self) -> i32 {
        self.entries[self.entries.len() - 1].1
    }
}
