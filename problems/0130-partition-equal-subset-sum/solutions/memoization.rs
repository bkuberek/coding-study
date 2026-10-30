/// Whether some elements of `nums[index..]` add up to exactly `remaining`.
fn reachable(index: usize, remaining: i32, nums: &[i32], memo: &mut [Vec<Option<bool>>]) -> bool {
    if remaining == 0 {
        return true;
    }
    if index == nums.len() || remaining < 0 {
        return false;
    }
    if let Some(known) = memo[index][remaining as usize] {
        return known;
    }
    let answer = reachable(index + 1, remaining - nums[index], nums, memo)
        || reachable(index + 1, remaining, nums, memo);
    memo[index][remaining as usize] = Some(answer);
    answer
}

pub fn can_partition(nums: Vec<i32>) -> bool {
    let total: i32 = nums.iter().sum();
    if total % 2 == 1 {
        return false;
    }
    let target = total / 2;
    // memo[index][remaining] is `None` until that state has been decided.
    let mut memo = vec![vec![None; target as usize + 1]; nums.len()];
    reachable(0, target, &nums, &mut memo)
}
