pub fn character_replacement(s: String, k: i32) -> i32 {
    let bytes = s.as_bytes();
    let k = k as usize;
    let mut best = 0;
    for target in b'A'..=b'Z' {
        if !bytes.contains(&target) {
            continue; // a letter that never occurs cannot start a better window
        }
        let (mut left, mut others) = (0, 0);
        for (right, &byte) in bytes.iter().enumerate() {
            if byte != target {
                others += 1;
            }
            while others > k {
                if bytes[left] != target {
                    others -= 1;
                }
                left += 1;
            }
            best = best.max(right + 1 - left);
        }
    }
    best as i32
}
