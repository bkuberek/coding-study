pub fn length_of_lis(nums: Vec<i32>) -> i32 {
    // ending[i] is the length of the longest increasing subsequence that ends at index i.
    let mut ending = vec![1; nums.len()];
    for i in 1..nums.len() {
        for j in 0..i {
            if nums[j] < nums[i] && ending[j] + 1 > ending[i] {
                ending[i] = ending[j] + 1;
            }
        }
    }
    ending.into_iter().max().unwrap_or(0)
}
