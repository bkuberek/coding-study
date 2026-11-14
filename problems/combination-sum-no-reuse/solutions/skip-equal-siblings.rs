pub fn combination_sum2(candidates: Vec<i32>, target: i32) -> Vec<Vec<i32>> {
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
    for i in start..ordered.len() {
        let value = ordered[i];
        if value > remaining {
            break;
        }
        // A second copy at the same level would rebuild the first copy's combinations.
        if i > start && value == ordered[i - 1] {
            continue;
        }
        chosen.push(value);
        extend(ordered, i + 1, remaining - value, chosen, result);
        chosen.pop();
    }
}
