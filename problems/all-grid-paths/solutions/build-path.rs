pub fn all_grid_paths(n: i32) -> Vec<String> {
    let last = n - 1;
    let mut paths = Vec::new();
    let mut moves = String::with_capacity(2 * last as usize);
    extend(last, 0, 0, &mut moves, &mut paths);
    paths
}

fn extend(last: i32, downs: i32, rights: i32, moves: &mut String, paths: &mut Vec<String>) {
    if downs == last && rights == last {
        paths.push(moves.clone());
        return;
    }
    // D is tried before R, so the paths come out in lexicographic order.
    if downs < last {
        moves.push('D');
        extend(last, downs + 1, rights, moves, paths);
        moves.pop();
    }
    if rights < last {
        moves.push('R');
        extend(last, downs, rights + 1, moves, paths);
        moves.pop();
    }
}
