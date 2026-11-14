pub fn climb_stairs(n: i32) -> i32 {
    let n = n as usize;
    // ways[step] counts the move sequences that end exactly on `step`.
    let mut ways = vec![0; n + 1];
    ways[0] = 1;
    ways[1] = 1;
    for step in 2..=n {
        ways[step] = ways[step - 1] + ways[step - 2];
    }
    ways[n]
}
