pub fn min_distance(word1: String, word2: String) -> i32 {
    let (word1, word2) = (word1.as_bytes(), word2.as_bytes());
    let (rows, columns) = (word1.len(), word2.len());
    // cost[i][j] is the distance between the prefixes word1[..i] and word2[..j]. Turning a prefix
    // into the empty word takes one deletion per character, and the reverse one insertion.
    let mut cost = vec![vec![0; columns + 1]; rows + 1];
    for (i, row) in cost.iter_mut().enumerate() {
        row[0] = i as i32;
    }
    for (j, entry) in cost[0].iter_mut().enumerate() {
        *entry = j as i32;
    }
    for i in 1..=rows {
        for j in 1..=columns {
            cost[i][j] = if word1[i - 1] == word2[j - 1] {
                cost[i - 1][j - 1]
            } else {
                1 + cost[i - 1][j].min(cost[i][j - 1]).min(cost[i - 1][j - 1])
            };
        }
    }
    cost[rows][columns]
}
