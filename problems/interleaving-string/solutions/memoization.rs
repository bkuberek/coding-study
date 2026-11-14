pub fn is_interleave(s1: String, s2: String, s3: String) -> bool {
    if s1.len() + s2.len() != s3.len() {
        return false;
    }
    // known[i][j] caches whether s1[i..] and s2[j..] interleave to s3[i + j..]; None is unknown.
    let mut known = vec![vec![None; s2.len() + 1]; s1.len() + 1];
    solve(
        0,
        0,
        s1.as_bytes(),
        s2.as_bytes(),
        s3.as_bytes(),
        &mut known,
    )
}

fn solve(
    i: usize,
    j: usize,
    s1: &[u8],
    s2: &[u8],
    s3: &[u8],
    known: &mut [Vec<Option<bool>>],
) -> bool {
    if i == s1.len() && j == s2.len() {
        return true;
    }
    if let Some(cached) = known[i][j] {
        return cached;
    }
    // The next character of s3 comes from s1 or from s2.
    let result = (i < s1.len() && s1[i] == s3[i + j] && solve(i + 1, j, s1, s2, s3, known))
        || (j < s2.len() && s2[j] == s3[i + j] && solve(i, j + 1, s1, s2, s3, known));
    known[i][j] = Some(result);
    result
}
