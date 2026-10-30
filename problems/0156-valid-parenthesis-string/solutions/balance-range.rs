pub fn check_valid_string(s: String) -> bool {
    // The possible open counts of the prefix are exactly the integers in [lowest, highest].
    let (mut lowest, mut highest) = (0, 0);
    for symbol in s.bytes() {
        match symbol {
            b'(' => {
                lowest += 1;
                highest += 1;
            }
            b')' => {
                lowest -= 1;
                highest -= 1;
            }
            _ => {
                lowest -= 1; // the wildcard as ")"
                highest += 1; // the wildcard as "("
            }
        }
        if highest < 0 {
            return false; // even with every wildcard as "(", too many ")"
        }
        lowest = lowest.max(0); // a negative count is not a real choice
    }
    lowest == 0
}
