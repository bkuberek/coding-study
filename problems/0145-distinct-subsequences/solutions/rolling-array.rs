pub fn num_distinct(s: String, t: String) -> i32 {
    let t = t.as_bytes();
    // ways[j] counts the occurrences of t[..j] in the prefix of s read so far.
    let mut ways = vec![0; t.len() + 1];
    ways[0] = 1;
    for &character in s.as_bytes() {
        // Right to left: ways[j - 1] still excludes this character, so it is used once.
        for j in (1..=t.len()).rev() {
            if t[j - 1] == character {
                ways[j] += ways[j - 1];
            }
        }
    }
    ways[t.len()]
}
