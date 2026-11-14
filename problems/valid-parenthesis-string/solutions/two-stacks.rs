pub fn check_valid_string(s: String) -> bool {
    let mut opens: Vec<usize> = Vec::new(); // positions of unmatched "("
    let mut stars: Vec<usize> = Vec::new(); // positions of unused "*"
    for (position, symbol) in s.bytes().enumerate() {
        match symbol {
            b'(' => opens.push(position),
            b'*' => stars.push(position),
            _ if !opens.is_empty() => {
                opens.pop(); // prefer a real "(" and keep wildcards for later
            }
            _ if !stars.is_empty() => {
                stars.pop();
            }
            _ => return false,
        }
    }
    // Every remaining "(" needs a later "*" to act as its ")".
    while let (Some(&open), Some(&star)) = (opens.last(), stars.last()) {
        opens.pop();
        stars.pop();
        if open > star {
            return false;
        }
    }
    opens.is_empty()
}
