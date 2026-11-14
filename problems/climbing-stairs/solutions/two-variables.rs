pub fn climb_stairs(n: i32) -> i32 {
    // Before each iteration: two_below and one_below count the ways to reach the two
    // steps just below the one being computed.
    let (mut two_below, mut one_below) = (1, 1);
    for _ in 2..=n {
        (two_below, one_below) = (one_below, one_below + two_below);
    }
    one_below
}
