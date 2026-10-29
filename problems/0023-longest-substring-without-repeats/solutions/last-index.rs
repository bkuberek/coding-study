const ASCII_SIZE: usize = 128;

pub fn length_of_longest_substring(s: String) -> i32 {
    let mut last_seen: [Option<usize>; ASCII_SIZE] = [None; ASCII_SIZE];
    let (mut left, mut best) = (0, 0);
    for (right, byte) in s.bytes().enumerate() {
        let ch = usize::from(byte);
        if let Some(previous) = last_seen[ch] {
            // Jump past the last occurrence, but never move the left edge backwards.
            left = left.max(previous + 1);
        }
        last_seen[ch] = Some(right);
        best = best.max(right - left + 1);
    }
    best as i32
}
