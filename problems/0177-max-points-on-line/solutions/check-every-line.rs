pub fn max_points(points: Vec<Vec<i32>>) -> i32 {
    if points.len() <= 2 {
        return points.len() as i32;
    }
    let mut best = 2;
    for (i, first) in points.iter().enumerate() {
        let (x1, y1) = (first[0], first[1]);
        for second in &points[i + 1..] {
            let (dx, dy) = (second[0] - x1, second[1] - y1);
            // (x, y) is on the line through both points when the cross product is zero.
            let on_line = points
                .iter()
                .filter(|point| dy * (point[0] - x1) == dx * (point[1] - y1))
                .count() as i32;
            best = best.max(on_line);
        }
    }
    best
}
