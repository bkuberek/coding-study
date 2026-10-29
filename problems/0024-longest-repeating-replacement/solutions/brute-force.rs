const ALPHABET_SIZE: usize = 26;

pub fn character_replacement(s: String, k: i32) -> i32 {
    let bytes = s.as_bytes();
    let k = k as usize;
    let mut best = 0;
    for start in 0..bytes.len() {
        let mut counts = [0usize; ALPHABET_SIZE];
        let mut most = 0;
        for (end, &byte) in bytes.iter().enumerate().skip(start) {
            let letter = usize::from(byte - b'A');
            counts[letter] += 1;
            most = most.max(counts[letter]);
            if end - start + 1 - most > k {
                break;
            }
            best = best.max(end - start + 1);
        }
    }
    best as i32
}
