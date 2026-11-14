pub fn three_sum(nums: Vec<i32>) -> Vec<Vec<i32>> {
    let mut values = nums;
    values.sort_unstable();
    let n = values.len();
    let mut triples = Vec::new();
    for i in 0..n.saturating_sub(2) {
        if i > 0 && values[i] == values[i - 1] {
            continue;
        }
        for j in i + 1..n - 1 {
            if j > i + 1 && values[j] == values[j - 1] {
                continue;
            }
            let third = -values[i] - values[j];
            // The membership test scans values[j + 1..]: one check per element.
            if values[j + 1..].contains(&third) {
                triples.push(vec![values[i], values[j], third]);
            }
        }
    }
    triples
}
