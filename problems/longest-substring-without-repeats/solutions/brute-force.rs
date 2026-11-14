const ASCII_SIZE: usize = 128;

pub fn length_of_longest_substring(s: String) -> i32 {
    let bytes = s.as_bytes();
    let mut best = 0;
    for start in 0..bytes.len() {
        let mut seen = [false; ASCII_SIZE];
        let mut end = start;
        while end < bytes.len() && !seen[usize::from(bytes[end])] {
            seen[usize::from(bytes[end])] = true;
            end += 1;
        }
        best = best.max(end - start);
    }
    best as i32
}
