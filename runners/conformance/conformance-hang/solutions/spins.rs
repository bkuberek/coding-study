pub fn wait_for(value: i32) -> i32 {
    while std::hint::black_box(value) < 0 {}
    value
}
