pub struct MinStack {
    values: Vec<i32>,
    /// The minimums in the order they took effect; the last one is the current minimum.
    minimums: Vec<i32>,
}

impl MinStack {
    pub fn new() -> Self {
        MinStack {
            values: Vec::new(),
            minimums: Vec::new(),
        }
    }

    pub fn push(&mut self, value: i32) {
        self.values.push(value);
        // `<=` keeps one copy per equal minimum, so popping one copy keeps the others.
        let is_new_minimum = match self.minimums.last() {
            Some(&minimum) => value <= minimum,
            None => true,
        };
        if is_new_minimum {
            self.minimums.push(value);
        }
    }

    pub fn pop(&mut self) {
        if self.values.pop() == self.minimums.last().copied() {
            self.minimums.pop();
        }
    }

    pub fn top(&mut self) -> i32 {
        self.values[self.values.len() - 1]
    }

    pub fn get_min(&mut self) -> i32 {
        self.minimums[self.minimums.len() - 1]
    }
}
