pub struct StressFailer {}

impl StressFailer {
    pub fn new() -> Self {
        StressFailer {}
    }

    pub fn step(&self, index: i32) -> i32 {
        if index == 100 {
            panic!("failed at {index}");
        }
        index
    }
}
