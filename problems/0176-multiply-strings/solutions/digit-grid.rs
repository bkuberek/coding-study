pub fn multiply(num1: String, num2: String) -> String {
    if num1 == "0" || num2 == "0" {
        return "0".to_string();
    }
    let first: Vec<u32> = num1.bytes().map(|ch| u32::from(ch - b'0')).collect();
    let second: Vec<u32> = num2.bytes().map(|ch| u32::from(ch - b'0')).collect();
    // digits[k] is result digit k counted from the left; the product has at most m + n digits.
    let mut digits = vec![0; first.len() + second.len()];
    for i in (0..first.len()).rev() {
        let mut carry = 0;
        for j in (0..second.len()).rev() {
            let total = digits[i + j + 1] + first[i] * second[j] + carry;
            digits[i + j + 1] = total % 10;
            carry = total / 10;
        }
        digits[i] += carry;
    }
    let start = if digits[0] == 0 { 1 } else { 0 }; // at most one leading zero
    digits[start..]
        .iter()
        .map(|&digit| char::from(b'0' + digit as u8))
        .collect()
}
