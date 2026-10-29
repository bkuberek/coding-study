const ASCII_SIZE: usize = 128;

pub fn min_window(s: String, t: String) -> String {
    let (s_bytes, t_bytes) = (s.as_bytes(), t.as_bytes());
    let mut deficit = [0i32; ASCII_SIZE];
    for &byte in t_bytes {
        deficit[usize::from(byte)] += 1;
    }
    // The positions of the letters that t contains: the window slides over these only.
    let useful: Vec<usize> = s_bytes
        .iter()
        .enumerate()
        .filter(|&(_, &byte)| deficit[usize::from(byte)] > 0)
        .map(|(index, _)| index)
        .collect();
    let mut missing = t_bytes.len();
    let (mut best_start, mut best_length) = (0, 0);
    let mut left = 0;
    for &right in &useful {
        let code = usize::from(s_bytes[right]);
        if deficit[code] > 0 {
            missing -= 1;
        }
        deficit[code] -= 1;
        while missing == 0 {
            let start = useful[left];
            if best_length == 0 || right + 1 - start < best_length {
                (best_start, best_length) = (start, right + 1 - start);
            }
            let leaving = usize::from(s_bytes[start]);
            deficit[leaving] += 1;
            if deficit[leaving] > 0 {
                missing += 1;
            }
            left += 1;
        }
    }
    s[best_start..best_start + best_length].to_string()
}
