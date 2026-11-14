pub fn my_pow(x: f64, n: i32) -> f64 {
    let base = if n >= 0 { x } else { 1.0 / x };
    // `unsigned_abs` is exact even for i32::MIN, where `-n` would overflow.
    let mut remaining = n.unsigned_abs();
    let mut result = 1.0;
    let mut done = 0;
    while done < remaining {
        result *= base;
        done += 1;
        if result == 1.0 {
            // base^done == 1, so the powers repeat with period done (x = 1 or x = -1).
            remaining = (remaining - done) % done;
            done = 0;
        } else if result == 0.0 || f64::is_infinite(result) {
            break; // further multiplications cannot change the result
        }
    }
    result
}
