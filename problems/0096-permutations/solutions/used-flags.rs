pub fn permute(nums: Vec<i32>) -> Vec<Vec<i32>> {
    let mut result = Vec::new();
    let mut ordering = Vec::with_capacity(nums.len());
    let mut used = vec![false; nums.len()];
    fill_next_slot(&nums, &mut used, &mut ordering, &mut result);
    result
}

fn fill_next_slot(
    nums: &[i32],
    used: &mut [bool],
    ordering: &mut Vec<i32>,
    result: &mut Vec<Vec<i32>>,
) {
    if ordering.len() == nums.len() {
        result.push(ordering.clone());
        return;
    }
    for (i, &value) in nums.iter().enumerate() {
        if used[i] {
            continue;
        }
        used[i] = true;
        ordering.push(value);
        fill_next_slot(nums, used, ordering, result);
        ordering.pop();
        used[i] = false;
    }
}
