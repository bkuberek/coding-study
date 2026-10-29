const ASCII_SIZE: usize = 128;

pub fn min_window(s: String, t: String) -> String {
    let (s_bytes, t_bytes) = (s.as_bytes(), t.as_bytes());
    let mut need = [0i32; ASCII_SIZE];
    for &byte in t_bytes {
        need[usize::from(byte)] += 1;
    }
    let (mut best_start, mut best_length) = (0, 0);
    for start in 0..s_bytes.len() {
        let mut remaining = need; // arrays are `Copy`: this copies the table
        let mut missing = t_bytes.len();
        for (end, &byte) in s_bytes.iter().enumerate().skip(start) {
            let code = usize::from(byte);
            if remaining[code] > 0 {
                missing -= 1;
            }
            remaining[code] -= 1;
            if missing == 0 {
                if best_length == 0 || end - start + 1 < best_length {
                    (best_start, best_length) = (start, end - start + 1);
                }
                break;
            }
        }
    }
    s[best_start..best_start + best_length].to_string()
}
