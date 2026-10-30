/// Little-endian digits of `digits * factor`.
fn times_digit(digits: &[u32], factor: u32) -> Vec<u32> {
    let mut product = Vec::with_capacity(digits.len() + 1);
    let mut carry = 0;
    for &digit in digits {
        let value = digit * factor + carry;
        product.push(value % 10);
        carry = value / 10;
    }
    if carry > 0 {
        product.push(carry);
    }
    product
}

/// Little-endian digits of `left + right`.
fn add(left: &[u32], right: &[u32]) -> Vec<u32> {
    let length = left.len().max(right.len());
    let mut total = Vec::with_capacity(length + 1);
    let mut carry = 0;
    for position in 0..length {
        let a = left.get(position).copied().unwrap_or(0);
        let b = right.get(position).copied().unwrap_or(0);
        let value = a + b + carry;
        total.push(value % 10);
        carry = value / 10;
    }
    if carry > 0 {
        total.push(carry);
    }
    total
}

pub fn multiply(num1: String, num2: String) -> String {
    if num1 == "0" || num2 == "0" {
        return "0".to_string();
    }
    let first: Vec<u32> = num1.bytes().rev().map(|ch| u32::from(ch - b'0')).collect();
    let mut total: Vec<u32> = Vec::new();
    // School method: one row per digit of num2, shifted by its position.
    for (shift, ch) in num2.bytes().rev().enumerate() {
        let mut row = vec![0; shift];
        row.extend(times_digit(&first, u32::from(ch - b'0')));
        total = add(&total, &row);
    }
    total
        .iter()
        .rev()
        .map(|&digit| char::from(b'0' + digit as u8))
        .collect()
}
