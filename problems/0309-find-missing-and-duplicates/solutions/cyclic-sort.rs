pub fn find_missing_and_duplicates(mut nums: Vec<i32>) -> Vec<Vec<i32>> {
    let n = nums.len();
    for i in 0..n {
        // Swap nums[i] to its home index nums[i] - 1 until the home already holds that value.
        // Comparing with the home, not with i, is what stops the loop on a repeated value.
        loop {
            let home = (nums[i] - 1) as usize;
            if nums[home] == nums[i] {
                break;
            }
            nums.swap(i, home);
        }
    }

    // Every value that occurs now sits at its home. A slot that holds another value is either
    // the home of a missing value or a spare copy of a value that is home elsewhere. A
    // negative sign on a home marks that its value has a spare copy.
    let mut missing = Vec::new();
    for i in 0..n {
        if nums[i].unsigned_abs() as usize == i + 1 {
            continue;
        }
        missing.push(i as i32 + 1);
        let spare = nums[i];
        nums[(spare - 1) as usize] = -spare;
    }

    // The marks are read in index order, so the duplicates come out sorted too.
    let duplicated = (0..n).filter(|&i| nums[i] < 0).map(|i| i as i32 + 1).collect();
    vec![missing, duplicated]
}
