pub fn combination_sum(candidates: Vec<i32>, target: i32) -> Vec<Vec<i32>> {
    let mut result = Vec::new();
    explore(&candidates, 0, target, &mut Vec::new(), &mut result);
    result
}

fn explore(
    candidates: &[i32],
    index: usize,
    remaining: i32,
    chosen: &mut Vec<i32>,
    result: &mut Vec<Vec<i32>>,
) {
    if remaining == 0 {
        result.push(chosen.clone());
        return;
    }
    if remaining < 0 || index == candidates.len() {
        return;
    }
    // Use candidates[index] once more and stay on it, since it may repeat.
    chosen.push(candidates[index]);
    explore(
        candidates,
        index,
        remaining - candidates[index],
        chosen,
        result,
    );
    chosen.pop();
    // Or never use it again.
    explore(candidates, index + 1, remaining, chosen, result);
}
