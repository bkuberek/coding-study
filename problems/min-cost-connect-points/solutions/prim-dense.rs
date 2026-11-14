pub fn min_cost_connect_points(points: Vec<Vec<i32>>) -> i32 {
    let n = points.len();
    // cheapest[i] is the cheapest cable from point i to the tree built so far.
    let mut cheapest = vec![i32::MAX; n];
    let mut in_tree = vec![false; n];
    cheapest[0] = 0;
    let mut total = 0;
    for _ in 0..n {
        let point = (0..n)
            .filter(|&i| !in_tree[i])
            .min_by_key(|&i| cheapest[i])
            .expect("every round adds one of n points, so an outside point remains");
        in_tree[point] = true;
        total += cheapest[point];
        let (x, y) = (points[point][0], points[point][1]);
        for other in 0..n {
            if !in_tree[other] {
                let cost = (x - points[other][0]).abs() + (y - points[other][1]).abs();
                cheapest[other] = cheapest[other].min(cost);
            }
        }
    }
    total
}
