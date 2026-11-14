pub fn num_distinct(s: String, t: String) -> i32 {
    let (s, t) = (s.as_bytes(), t.as_bytes());
    let (rows, columns) = (s.len(), t.len());
    // ways[i][j] counts the occurrences of t[..j] in s[..i]; the empty t[..0] occurs once.
    let mut ways = vec![vec![0; columns + 1]; rows + 1];
    for row in ways.iter_mut() {
        row[0] = 1;
    }
    for i in 1..=rows {
        for j in 1..=columns {
            // Occurrences that skip s[i - 1], plus those that match it with t[j - 1].
            ways[i][j] = ways[i - 1][j];
            if s[i - 1] == t[j - 1] {
                ways[i][j] += ways[i - 1][j - 1];
            }
        }
    }
    ways[rows][columns]
}
