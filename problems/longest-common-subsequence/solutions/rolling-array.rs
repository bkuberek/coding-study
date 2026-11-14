pub fn longest_common_subsequence(text1: String, text2: String) -> i32 {
    // The answer is symmetric, so let the rows run along the shorter string.
    let (longer, shorter) = if text1.len() >= text2.len() {
        (text1.as_bytes(), text2.as_bytes())
    } else {
        (text2.as_bytes(), text1.as_bytes())
    };
    // previous[j] is the answer for the prefixes longer[..i] and shorter[..j]; current is the
    // row being filled, and the two swap after every character of longer.
    let mut previous = vec![0; shorter.len() + 1];
    let mut current = vec![0; shorter.len() + 1];
    for &character in longer {
        for (j, &other) in shorter.iter().enumerate() {
            current[j + 1] = if character == other {
                previous[j] + 1
            } else {
                previous[j + 1].max(current[j])
            };
        }
        std::mem::swap(&mut previous, &mut current);
    }
    previous[shorter.len()]
}
