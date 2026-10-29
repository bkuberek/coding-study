pub fn k_closest(points: Vec<Vec<i32>>, k: i32) -> Vec<Vec<i32>> {
    // Squared distances order points exactly like distances, without square roots.
    let mut sorted = points;
    sorted.sort_unstable_by_key(|point| squared(point));
    sorted.truncate(k as usize);
    sorted
}

fn squared(point: &[i32]) -> i32 {
    point[0] * point[0] + point[1] * point[1]
}
