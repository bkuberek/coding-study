pub fn can_jump(nums: Vec<i32>) -> bool {
    let mut farthest = 0; // every index up to `farthest` is reachable
    for (i, &jump) in nums.iter().enumerate() {
        if i > farthest {
            return false;
        }
        farthest = farthest.max(i + jump as usize);
    }
    true
}
