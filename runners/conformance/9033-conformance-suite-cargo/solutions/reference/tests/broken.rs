//! A test file that does not compile: its target fails, and every other target still runs.

#[test]
fn does_not_compile() {
    let count: i32 = "three";
    assert_eq!(count, 3);
}
