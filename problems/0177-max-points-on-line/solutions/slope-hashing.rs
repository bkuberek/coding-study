use std::collections::HashMap;

/// The greatest common divisor of a and b as a non-negative number.
fn gcd(a: i32, b: i32) -> i32 {
    let (mut a, mut b) = (a.abs(), b.abs());
    while b != 0 {
        (a, b) = (b, a % b);
    }
    a
}

pub fn max_points(points: Vec<Vec<i32>>) -> i32 {
    let mut best = 1;
    for (i, anchor) in points.iter().enumerate() {
        let mut directions: HashMap<(i32, i32), i32> = HashMap::new();
        for other in &points[i + 1..] {
            let (mut dx, mut dy) = (other[0] - anchor[0], other[1] - anchor[1]);
            let divisor = gcd(dx, dy); // never 0: the points are distinct
            (dx, dy) = (dx / divisor, dy / divisor);
            // One representative per direction: dx > 0, or dx == 0 and dy > 0.
            if dx < 0 || (dx == 0 && dy < 0) {
                (dx, dy) = (-dx, -dy);
            }
            *directions.entry((dx, dy)).or_insert(0) += 1;
        }
        if let Some(&most) = directions.values().max() {
            best = best.max(most + 1); // + 1 for the anchor
        }
    }
    best
}
