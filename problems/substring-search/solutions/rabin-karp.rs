const BASE: u64 = 131;
const MODULUS: u64 = 1_000_000_007;

pub fn find_all_occurrences(text: String, pattern: String) -> Vec<i32> {
    let (text, pattern) = (text.as_bytes(), pattern.as_bytes());
    let window_size = pattern.len();
    if window_size > text.len() {
        return Vec::new();
    }
    let mut leaving_weight = 1;
    for _ in 1..window_size {
        leaving_weight = leaving_weight * BASE % MODULUS;
    }
    let (mut target, mut window) = (0, 0);
    for i in 0..window_size {
        target = (target * BASE + u64::from(pattern[i])) % MODULUS;
        window = (window * BASE + u64::from(text[i])) % MODULUS;
    }
    let mut found = Vec::new();
    for start in 0..=text.len() - window_size {
        if window == target && text[start..start + window_size] == *pattern {
            found.push(start as i32);
        }
        if start + window_size < text.len() {
            let leaving = u64::from(text[start]) * leaving_weight % MODULUS;
            let without = (window + MODULUS - leaving) % MODULUS;
            window = (without * BASE + u64::from(text[start + window_size])) % MODULUS;
        }
    }
    found
}
