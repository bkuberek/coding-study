pub fn longest_common_subsequence(text1: String, text2: String) -> i32 {
    let (text1, text2) = (text1.as_bytes(), text2.as_bytes());
    let (rows, columns) = (text1.len(), text2.len());
    // best[i][j] is the answer for the prefixes text1[..i] and text2[..j]; row and column 0
    // stand for an empty prefix.
    let mut best = vec![vec![0; columns + 1]; rows + 1];
    for i in 1..=rows {
        for j in 1..=columns {
            best[i][j] = if text1[i - 1] == text2[j - 1] {
                best[i - 1][j - 1] + 1
            } else {
                best[i - 1][j].max(best[i][j - 1])
            };
        }
    }
    best[rows][columns]
}
