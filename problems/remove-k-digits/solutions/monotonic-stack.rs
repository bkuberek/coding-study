pub fn remove_k_digits(num: String, k: i32) -> String {
    // The digits kept so far; they never decrease from bottom to top.
    let mut kept: Vec<char> = Vec::with_capacity(num.len());
    let mut remaining = k as usize;
    for digit in num.chars() {
        while remaining > 0 && kept.last().is_some_and(|&last| last > digit) {
            kept.pop();
            remaining -= 1;
        }
        kept.push(digit);
    }
    // The kept digits never decrease, so leftover deletions are cheapest at the end.
    kept.truncate(kept.len() - remaining);
    let trimmed: String = kept.into_iter().skip_while(|&digit| digit == '0').collect();
    if trimmed.is_empty() {
        "0".to_string()
    } else {
        trimmed
    }
}
