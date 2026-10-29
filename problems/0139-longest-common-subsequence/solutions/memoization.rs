pub fn longest_common_subsequence(text1: String, text2: String) -> i32 {
    // best[i][j] caches the answer for the suffixes text1[i..] and text2[j..]; None is unknown.
    let mut best = vec![vec![None; text2.len()]; text1.len()];
    solve(0, 0, text1.as_bytes(), text2.as_bytes(), &mut best)
}

fn solve(i: usize, j: usize, text1: &[u8], text2: &[u8], best: &mut [Vec<Option<i32>>]) -> i32 {
    if i == text1.len() || j == text2.len() {
        return 0;
    }
    if let Some(known) = best[i][j] {
        return known;
    }
    let result = if text1[i] == text2[j] {
        1 + solve(i + 1, j + 1, text1, text2, best)
    } else {
        solve(i + 1, j, text1, text2, best).max(solve(i, j + 1, text1, text2, best))
    };
    best[i][j] = Some(result);
    result
}
