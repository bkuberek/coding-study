pub fn is_interleave(s1: String, s2: String, s3: String) -> bool {
    let (rows, columns) = (s1.len(), s2.len());
    if rows + columns != s3.len() {
        return false;
    }
    let (s1, s2, s3) = (s1.as_bytes(), s2.as_bytes(), s3.as_bytes());
    // reach[i][j]: s1[..i] and s2[..j] interleave to s3[..i + j].
    let mut reach = vec![vec![false; columns + 1]; rows + 1];
    reach[0][0] = true;
    for i in 0..=rows {
        for j in 0..=columns {
            // The last character of s3[..i + j] came from s1 or from s2.
            let from_s1 = i > 0 && reach[i - 1][j] && s1[i - 1] == s3[i + j - 1];
            let from_s2 = j > 0 && reach[i][j - 1] && s2[j - 1] == s3[i + j - 1];
            if from_s1 || from_s2 {
                reach[i][j] = true;
            }
        }
    }
    reach[rows][columns]
}
