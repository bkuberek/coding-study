pub fn subsets(nums: Vec<i32>) -> Vec<Vec<i32>> {
    let mut result = Vec::new();
    explore(&nums, 0, &mut Vec::new(), &mut result);
    result
}

fn explore(nums: &[i32], index: usize, chosen: &mut Vec<i32>, result: &mut Vec<Vec<i32>>) {
    if index == nums.len() {
        result.push(chosen.clone());
        return;
    }
    chosen.push(nums[index]);
    explore(nums, index + 1, chosen, result);
    chosen.pop();
    explore(nums, index + 1, chosen, result);
}
