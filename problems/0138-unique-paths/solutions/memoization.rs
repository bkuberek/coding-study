const MOD: i32 = 1_000_000_007;

pub fn unique_paths(m: i32, n: i32) -> i32 {
    // routes[row][column] caches the number of routes from that cell to the goal; None is unknown.
    let mut routes = vec![vec![None; n as usize]; m as usize];
    count(0, 0, &mut routes)
}

fn count(row: usize, column: usize, routes: &mut [Vec<Option<i32>>]) -> i32 {
    if row == routes.len() - 1 || column == routes[0].len() - 1 {
        return 1;
    }
    if let Some(known) = routes[row][column] {
        return known;
    }
    // Two residues below MOD add up to less than 2^31, so `i32` holds the sum.
    let total = (count(row + 1, column, routes) + count(row, column + 1, routes)) % MOD;
    routes[row][column] = Some(total);
    total
}
