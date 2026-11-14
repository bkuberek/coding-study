// Whether the pattern letter matches the character.
fn fits(letter: u8, character: u8) -> bool {
    letter == character || letter == b'.'
}

pub fn is_match(s: String, p: String) -> bool {
    let (s, p) = (s.as_bytes(), p.as_bytes());
    let columns = p.len();
    // previous[j]: s[..i - 1] matches p[..j]; current[j]: s[..i] matches p[..j]. The two swap
    // after every character of s; row 0 never reads previous, and every cell of current is
    // rewritten.
    let mut previous = vec![false; columns + 1];
    let mut current = vec![false; columns + 1];
    for i in 0..=s.len() {
        current[0] = i == 0;
        for j in 1..=columns {
            current[j] = if p[j - 1] == b'*' {
                // "x*" matches nothing, or it matches s[i - 1] and possibly more before it.
                current[j - 2] || (i > 0 && fits(p[j - 2], s[i - 1]) && previous[j])
            } else {
                i > 0 && fits(p[j - 1], s[i - 1]) && previous[j - 1]
            };
        }
        std::mem::swap(&mut previous, &mut current);
    }
    previous[columns]
}
