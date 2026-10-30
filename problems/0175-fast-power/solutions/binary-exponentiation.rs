pub fn my_pow(x: f64, n: i32) -> f64 {
    let mut base = if n >= 0 { x } else { 1.0 / x };
    // `unsigned_abs` is exact even for i32::MIN, where `-n` would overflow.
    let mut exponent = n.unsigned_abs();
    let mut result = 1.0;
    // Invariant: result * base^exponent equals the original x^n.
    while exponent > 0 {
        if exponent & 1 == 1 {
            result *= base;
        }
        base *= base;
        exponent >>= 1;
    }
    result
}
