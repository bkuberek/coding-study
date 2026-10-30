pub fn get_sum(a: i32, b: i32) -> i32 {
    // Work on the 32-bit patterns: a u32 drops the bit shifted out of position 31, so a
    // negative carry dies out instead of growing.
    let (mut x, mut y) = (a as u32, b as u32);
    while y != 0 {
        let carry = (x & y) << 1;
        x ^= y; // the sum of every column, ignoring carries
        y = carry;
    }
    // A set sign bit means a negative value: reading the pattern as an i32 recovers it.
    x as i32
}
