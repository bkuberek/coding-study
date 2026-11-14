pub fn min_sub_array_len(target: i32, nums: Vec<i32>) -> i32 {
    let mut best = 0;
    for start in 0..nums.len() {
        let mut total = 0;
        for (end, &value) in nums.iter().enumerate().skip(start) {
            total += value;
            if total >= target {
                if best == 0 || end - start + 1 < best {
                    best = end - start + 1;
                }
                break;
            }
        }
    }
    best as i32
}
