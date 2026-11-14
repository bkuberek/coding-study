pub fn is_palindrome(s: String) -> bool {
    let cleaned: Vec<char> = s
        .chars()
        .filter(char::is_ascii_alphanumeric)
        .map(|character| character.to_ascii_lowercase())
        .collect();
    cleaned.iter().eq(cleaned.iter().rev())
}
