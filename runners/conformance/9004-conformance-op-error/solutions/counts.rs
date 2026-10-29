pub struct Counter {
    count: i32,
}

impl Counter {
    pub fn new() -> Self {
        Counter { count: 0 }
    }

    pub fn increment(&mut self) -> i32 {
        self.count += 1;
        self.count
    }

    pub fn fail(&mut self) -> i32 {
        panic!("counter failure")
    }
}
