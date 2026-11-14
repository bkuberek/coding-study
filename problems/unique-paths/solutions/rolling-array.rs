const MOD: i32 = 1_000_000_007;

pub fn unique_paths(m: i32, n: i32) -> i32 {
    // Transposing the grid does not change the count, so keep the row along the shorter side.
    let (width, height) = (m.min(n) as usize, m.max(n) as usize);
    // Before the update, routes[column] belongs to the row above; after it, to the current row.
    let mut routes = vec![1; width];
    for _ in 1..height {
        for column in 1..width {
            // Two residues below MOD add up to less than 2^31, so `i32` holds the sum.
            routes[column] = (routes[column] + routes[column - 1]) % MOD;
        }
    }
    routes[width - 1]
}
