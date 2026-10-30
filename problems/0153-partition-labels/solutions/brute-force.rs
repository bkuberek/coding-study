pub fn partition_labels(s: String) -> Vec<i32> {
    let bytes = s.as_bytes();
    let mut sizes = Vec::new();
    let mut start = 0;
    while start < bytes.len() {
        // The piece must reach the last copy of every letter it contains.
        let mut end = last_index(bytes, bytes[start]);
        let mut position = start;
        while position <= end {
            end = end.max(last_index(bytes, bytes[position]));
            position += 1;
        }
        sizes.push((end + 1 - start) as i32);
        start = end + 1;
    }
    sizes
}

// The position of the last copy of the letter; the letter always occurs, since it comes from
// the string.
fn last_index(bytes: &[u8], letter: u8) -> usize {
    bytes
        .iter()
        .rposition(|&byte| byte == letter)
        .expect("the letter occurs in the string")
}
