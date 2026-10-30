pub fn subsets(nums: Vec<i32>) -> Vec<Vec<i32>> {
    // Bit i of mask says whether nums[i] belongs to the subset that mask encodes.
    (0..1u32 << nums.len())
        .map(|mask| {
            nums.iter()
                .enumerate()
                .filter(|&(i, _)| (mask >> i) & 1 == 1)
                .map(|(_, &value)| value)
                .collect()
        })
        .collect()
}
