pub fn check_valid_string(s: String) -> bool {
    let s = s.as_bytes();
    // possible[k] is true when some choice of wildcards leaves k parentheses open after the
    // prefix; following is the same table for the next prefix. No count exceeds s.len().
    let mut possible = vec![false; s.len() + 1];
    let mut following = vec![false; s.len() + 1];
    possible[0] = true;
    for &symbol in s {
        following.fill(false);
        let mut reachable = false;
        for open in 0..possible.len() {
            if !possible[open] {
                continue;
            }
            if symbol == b'(' || symbol == b'*' {
                following[open + 1] = true;
                reachable = true;
            }
            if (symbol == b')' || symbol == b'*') && open > 0 {
                following[open - 1] = true;
                reachable = true;
            }
            if symbol == b'*' {
                following[open] = true;
                reachable = true;
            }
        }
        std::mem::swap(&mut possible, &mut following);
        if !reachable {
            return false;
        }
    }
    possible[0]
}
