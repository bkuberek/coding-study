pub fn num_distinct(s: String, t: String) -> i32 {
    // ways[i][j] caches the occurrences of t[j..] as a subsequence of s[i..]; None is unknown.
    let mut ways = vec![vec![None; t.len()]; s.len()];
    count(0, 0, s.as_bytes(), t.as_bytes(), &mut ways)
}

fn count(i: usize, j: usize, s: &[u8], t: &[u8], ways: &mut [Vec<Option<i32>>]) -> i32 {
    if j == t.len() {
        return 1; // the empty suffix of t occurs once
    }
    if s.len() - i < t.len() - j {
        return 0; // not enough characters left in s
    }
    if let Some(known) = ways[i][j] {
        return known;
    }
    // Either s[i] is skipped, or it is matched with t[j].
    let mut result = count(i + 1, j, s, t, ways);
    if s[i] == t[j] {
        result += count(i + 1, j + 1, s, t, ways);
    }
    ways[i][j] = Some(result);
    result
}
