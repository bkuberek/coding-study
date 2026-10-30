// Whether the pattern letter matches the character.
fn fits(letter: u8, character: u8) -> bool {
    letter == character || letter == b'.'
}

pub fn is_match(s: String, p: String) -> bool {
    let (s, p) = (s.as_bytes(), p.as_bytes());
    let (rows, columns) = (s.len(), p.len());
    // matches[i][j]: s[..i] matches p[..j].
    let mut matches = vec![vec![false; columns + 1]; rows + 1];
    matches[0][0] = true;
    for i in 0..=rows {
        for j in 1..=columns {
            matches[i][j] = if p[j - 1] == b'*' {
                // "x*" matches nothing, or it matches s[i - 1] and possibly more before it.
                matches[i][j - 2] || (i > 0 && fits(p[j - 2], s[i - 1]) && matches[i - 1][j])
            } else {
                i > 0 && fits(p[j - 1], s[i - 1]) && matches[i - 1][j - 1]
            };
        }
    }
    matches[rows][columns]
}
