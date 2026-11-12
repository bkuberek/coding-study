pub fn lamp_patterns(n: i32) -> Vec<String> {
    let mut result = Vec::new();
    for number in 0..(1_u32 << n) {
        // Counting up writes the strings in increasing order; the bits are the lamps.
        let pattern = format!("{:0width$b}", number, width = n as usize);
        if !pattern.contains("11") {
            result.push(pattern);
        }
    }
    result
}
