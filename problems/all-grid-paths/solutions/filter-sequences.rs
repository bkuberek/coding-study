pub fn all_grid_paths(n: i32) -> Vec<String> {
    let steps = 2 * (n - 1) as u32;
    let mut paths = Vec::new();
    // Counting up from 0 reads the bits from the most significant one as the first move, with
    // 0 for D and 1 for R, so the sequences come out in lexicographic order.
    for pattern in 0..1u32 << steps {
        let moves: String = (0..steps)
            .map(|step| if (pattern >> (steps - 1 - step)) & 1 == 1 { 'R' } else { 'D' })
            .collect();
        if moves.matches('R').count() == (n - 1) as usize {
            paths.push(moves);
        }
    }
    paths
}
