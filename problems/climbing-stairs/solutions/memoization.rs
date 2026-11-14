fn ways(step: usize, memo: &mut [i32]) -> i32 {
    // One way to stand on the ground (step 0), one way to reach step 1.
    if step <= 1 {
        return 1;
    }
    if memo[step] == 0 {
        memo[step] = ways(step - 1, memo) + ways(step - 2, memo);
    }
    memo[step]
}

pub fn climb_stairs(n: i32) -> i32 {
    let n = n as usize;
    // 0 means "not computed yet": every step has at least one way.
    let mut memo = vec![0; n + 1];
    ways(n, &mut memo)
}
