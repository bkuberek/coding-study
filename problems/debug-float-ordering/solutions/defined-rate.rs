pub fn rank_creatives(ids: Vec<i32>, impressions: Vec<i32>, clicks: Vec<i32>) -> Vec<i32> {
    let mut ranked: Vec<(i32, f64)> = ids
        .iter()
        .zip(impressions.iter().zip(&clicks))
        .map(|(&id, (&shown, &clicked))| (id, click_rate(clicked, shown)))
        .collect();
    // total_cmp is a total order on every f64, so the comparator never has a case to unwrap.
    ranked.sort_by(|a, b| b.1.total_cmp(&a.1).then(a.0.cmp(&b.0)));
    ranked.into_iter().map(|(id, _)| id).collect()
}

/// Clicks per impression, and 0 for a creative that was never shown: 0.0 / 0.0 would be NaN.
fn click_rate(clicked: i32, shown: i32) -> f64 {
    if shown == 0 {
        0.0
    } else {
        f64::from(clicked) / f64::from(shown)
    }
}
