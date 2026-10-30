// Debug: Float Ordering. Some tests fail: find the bug and fix it.
pub fn rank_creatives(ids: Vec<i32>, impressions: Vec<i32>, clicks: Vec<i32>) -> Vec<i32> {
    let mut ranked: Vec<(i32, f64)> = ids
        .iter()
        .zip(impressions.iter().zip(&clicks))
        .map(|(&id, (&shown, &clicked))| (id, f64::from(clicked) / f64::from(shown)))
        .collect();
    ranked.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap().then(a.0.cmp(&b.0)));
    ranked.into_iter().map(|(id, _)| id).collect()
}
