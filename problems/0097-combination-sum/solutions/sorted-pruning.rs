pub fn combination_sum(candidates: Vec<i32>, target: i32) -> Vec<Vec<i32>> {
    let mut ordered = candidates;
    ordered.sort_unstable();
    let mut result = Vec::new();
    extend(&ordered, 0, target, &mut Vec::new(), &mut result);
    result
}

fn extend(
    ordered: &[i32],
    start: usize,
    remaining: i32,
    chosen: &mut Vec<i32>,
    result: &mut Vec<Vec<i32>>,
) {
    if remaining == 0 {
        result.push(chosen.clone());
        return;
    }
    // Values are added in non-decreasing order, so each combination is built once.
    for (i, &value) in ordered.iter().enumerate().skip(start) {
        if value > remaining {
            break;
        }
        chosen.push(value);
        extend(ordered, i, remaining - value, chosen, result);
        chosen.pop();
    }
}
