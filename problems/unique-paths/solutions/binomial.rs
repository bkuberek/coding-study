const MOD: i64 = 1_000_000_007;

pub fn unique_paths(m: i32, n: i32) -> i32 {
    let (m, n) = (i64::from(m), i64::from(n));
    // A route is a sequence of m + n - 2 moves; choose which of them are the shorter direction.
    let moves = m + n - 2;
    let chosen = m.min(n) - 1;
    let (mut numerator, mut denominator) = (1, 1);
    for step in 1..=chosen {
        numerator = numerator * (moves - chosen + step) % MOD;
        denominator = denominator * step % MOD;
    }
    // MOD is prime, so denominator^(MOD - 2) is its inverse (Fermat's little theorem).
    (numerator * mod_pow(denominator, MOD - 2) % MOD) as i32
}

// base^exponent mod MOD by square-and-multiply; products of two residues stay below 2^63.
fn mod_pow(mut base: i64, mut exponent: i64) -> i64 {
    let mut result = 1;
    base %= MOD;
    while exponent > 0 {
        if exponent & 1 == 1 {
            result = result * base % MOD;
        }
        base = base * base % MOD;
        exponent >>= 1;
    }
    result
}
