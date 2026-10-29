pub fn min_distance(word1: String, word2: String) -> i32 {
    // cost[i][j] caches the distance between the suffixes word1[i..] and word2[j..]; None is unknown.
    let mut cost = vec![vec![None; word2.len() + 1]; word1.len() + 1];
    solve(0, 0, word1.as_bytes(), word2.as_bytes(), &mut cost)
}

fn solve(i: usize, j: usize, word1: &[u8], word2: &[u8], cost: &mut [Vec<Option<i32>>]) -> i32 {
    if i == word1.len() {
        return (word2.len() - j) as i32; // insert the rest of word2
    }
    if j == word2.len() {
        return (word1.len() - i) as i32; // delete the rest of word1
    }
    if let Some(known) = cost[i][j] {
        return known;
    }
    let result = if word1[i] == word2[j] {
        solve(i + 1, j + 1, word1, word2, cost)
    } else {
        1 + solve(i + 1, j, word1, word2, cost) // delete word1[i]
            .min(solve(i, j + 1, word1, word2, cost)) // insert word2[j]
            .min(solve(i + 1, j + 1, word1, word2, cost)) // replace word1[i] with word2[j]
    };
    cost[i][j] = Some(result);
    result
}
