const MOD: i32 = 1_000_000_007;

pub fn unique_paths(m: i32, n: i32) -> i32 {
    let (rows, columns) = (m as usize, n as usize);
    // routes[row][column] is the number of routes from the start to that cell. The first row
    // and the first column can only be reached in a straight line.
    let mut routes = vec![vec![1; columns]; rows];
    for row in 1..rows {
        for column in 1..columns {
            // Two residues below MOD add up to less than 2^31, so `i32` holds the sum.
            routes[row][column] = (routes[row - 1][column] + routes[row][column - 1]) % MOD;
        }
    }
    routes[rows - 1][columns - 1]
}
