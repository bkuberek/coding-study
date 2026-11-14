pub fn is_interleave(s1: String, s2: String, s3: String) -> bool {
    if s1.len() + s2.len() != s3.len() {
        return false;
    }
    // Swapping the sources does not change the answer, so let the row run along the shorter.
    let (longer, shorter) = if s1.len() >= s2.len() {
        (s1.as_bytes(), s2.as_bytes())
    } else {
        (s2.as_bytes(), s1.as_bytes())
    };
    let s3 = s3.as_bytes();
    // Before row i is processed, reach[j] tells whether longer[..i - 1] and shorter[..j]
    // interleave to s3[..i - 1 + j]; afterwards it holds row i.
    let mut reach = vec![false; shorter.len() + 1];
    for i in 0..=longer.len() {
        for j in 0..=shorter.len() {
            if i == 0 && j == 0 {
                reach[j] = true;
                continue;
            }
            let from_longer = i > 0 && reach[j] && longer[i - 1] == s3[i + j - 1];
            let from_shorter = j > 0 && reach[j - 1] && shorter[j - 1] == s3[i + j - 1];
            reach[j] = from_longer || from_shorter;
        }
    }
    reach[shorter.len()]
}
