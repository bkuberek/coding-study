pub fn longest_ones(nums: Vec<i32>, k: i32) -> i32 {
    let mut best = 0;
    for start in 0..nums.len() {
        let mut zeros = 0;
        let mut end = start;
        while end < nums.len() {
            if nums[end] == 0 {
                if zeros == k {
                    break;
                }
                zeros += 1;
            }
            end += 1;
        }
        best = best.max(end - start);
    }
    best as i32
}
