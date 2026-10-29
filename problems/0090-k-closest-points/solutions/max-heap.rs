use std::collections::BinaryHeap;

pub fn k_closest(mut points: Vec<Vec<i32>>, k: i32) -> Vec<Vec<i32>> {
    let k = k as usize;
    // The heap keeps (squared distance, position) of the k closest points seen; its root is the
    // farthest of them.
    let mut kept: BinaryHeap<(i32, usize)> = BinaryHeap::with_capacity(k);
    for (index, point) in points.iter().enumerate() {
        let distance = point[0] * point[0] + point[1] * point[1];
        if kept.len() < k {
            kept.push((distance, index));
        } else if let Some(mut farthest) = kept.peek_mut() {
            if distance < farthest.0 {
                *farthest = (distance, index);
            }
        }
    }
    kept.into_iter()
        .map(|(_, index)| std::mem::take(&mut points[index]))
        .collect()
}
