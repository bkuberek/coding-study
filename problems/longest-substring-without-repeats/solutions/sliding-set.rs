const ASCII_SIZE: usize = 128;

pub fn length_of_longest_substring(s: String) -> i32 {
    let bytes = s.as_bytes();
    let mut in_window = [false; ASCII_SIZE];
    let (mut left, mut best) = (0, 0);
    for (right, &byte) in bytes.iter().enumerate() {
        let ch = usize::from(byte);
        while in_window[ch] {
            in_window[usize::from(bytes[left])] = false;
            left += 1;
        }
        in_window[ch] = true;
        best = best.max(right - left + 1);
    }
    best as i32
}
