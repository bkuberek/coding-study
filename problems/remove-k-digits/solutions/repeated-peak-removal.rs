pub fn remove_k_digits(num: String, k: i32) -> String {
    let mut digits: Vec<char> = num.chars().collect();
    for _ in 0..k {
        // The first digit larger than its successor, or the last digit if none is.
        let mut peak = 0;
        while peak + 1 < digits.len() && digits[peak] <= digits[peak + 1] {
            peak += 1;
        }
        digits.remove(peak);
    }
    without_leading_zeros(digits)
}

fn without_leading_zeros(digits: Vec<char>) -> String {
    let trimmed: String = digits
        .into_iter()
        .skip_while(|&digit| digit == '0')
        .collect();
    if trimmed.is_empty() {
        "0".to_string()
    } else {
        trimmed
    }
}
