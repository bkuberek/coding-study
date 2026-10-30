pub fn is_match(s: String, p: String) -> bool {
    // known[i][j] caches whether s[i..] matches p[j..]; None is unknown.
    let mut known = vec![vec![None; p.len() + 1]; s.len() + 1];
    solve(0, 0, s.as_bytes(), p.as_bytes(), &mut known)
}

fn solve(i: usize, j: usize, s: &[u8], p: &[u8], known: &mut [Vec<Option<bool>>]) -> bool {
    if j == p.len() {
        return i == s.len();
    }
    if let Some(cached) = known[i][j] {
        return cached;
    }
    let first = i < s.len() && (p[j] == s[i] || p[j] == b'.');
    let result = if j + 1 < p.len() && p[j + 1] == b'*' {
        // Skip "x*" entirely, or let it eat one more character and stay on it.
        solve(i, j + 2, s, p, known) || (first && solve(i + 1, j, s, p, known))
    } else {
        first && solve(i + 1, j + 1, s, p, known)
    };
    known[i][j] = Some(result);
    result
}
