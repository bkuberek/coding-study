pub fn longest_palindrome(s: String) -> String {
    let bytes = s.as_bytes();
    let n = bytes.len();
    // is_palindrome[i][j] tells whether s[i..=j] is a palindrome.
    let mut is_palindrome = vec![vec![false; n]; n];
    for (i, row) in is_palindrome.iter_mut().enumerate() {
        row[i] = true;
    }
    let (mut best_start, mut best_length) = (0, 1);
    for length in 2..=n {
        for i in 0..=n - length {
            let j = i + length - 1;
            if bytes[i] == bytes[j] && (length == 2 || is_palindrome[i + 1][j - 1]) {
                is_palindrome[i][j] = true;
                best_start = i;
                best_length = length;
            }
        }
    }
    s[best_start..best_start + best_length].to_string()
}
