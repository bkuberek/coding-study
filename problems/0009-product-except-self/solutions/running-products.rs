pub fn product_except_self(nums: Vec<i32>) -> Vec<i32> {
    let n = nums.len();
    let mut answer = vec![1; n];
    for i in 1..n {
        answer[i] = answer[i - 1] * nums[i - 1]; // product of nums[..i]
    }
    let mut after = 1; // product of nums[i + 1..]
    for i in (0..n).rev() {
        answer[i] *= after;
        after *= nums[i];
    }
    answer
}
