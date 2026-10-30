pub fn subsets_with_dup(nums: Vec<i32>) -> Vec<Vec<i32>> {
    let mut ordered = nums;
    ordered.sort_unstable();
    let mut result = Vec::new();
    extend(&ordered, 0, &mut Vec::new(), &mut result);
    result
}

fn extend(ordered: &[i32], start: usize, chosen: &mut Vec<i32>, result: &mut Vec<Vec<i32>>) {
    // Every node of this recursion is a distinct subset.
    result.push(chosen.clone());
    for i in start..ordered.len() {
        // A second copy at the same level would rebuild the first copy's subtree.
        if i > start && ordered[i] == ordered[i - 1] {
            continue;
        }
        chosen.push(ordered[i]);
        extend(ordered, i + 1, chosen, result);
        chosen.pop();
    }
}
