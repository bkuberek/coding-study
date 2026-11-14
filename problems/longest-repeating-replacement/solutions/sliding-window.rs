const ALPHABET_SIZE: usize = 26;

pub fn character_replacement(s: String, k: i32) -> i32 {
    let bytes = s.as_bytes();
    let k = k as usize;
    let mut counts = [0usize; ALPHABET_SIZE];
    let (mut most, mut left, mut best) = (0, 0, 0);
    for (right, &byte) in bytes.iter().enumerate() {
        let letter = usize::from(byte - b'A');
        counts[letter] += 1;
        most = most.max(counts[letter]);
        if right - left + 1 - most > k {
            counts[usize::from(bytes[left] - b'A')] -= 1;
            left += 1;
        }
        best = best.max(right - left + 1);
    }
    best as i32
}
