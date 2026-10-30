pub fn count_smaller(nums: Vec<i32>) -> Vec<i32> {
    let n = nums.len();
    let mut counts = vec![0; n];
    let mut order: Vec<usize> = (0..n).collect(); // positions, sorted by value within each merged run
    let mut buffer = vec![0; n];
    // Bottom-up merge sort of positions by value; no recursion needed.
    let mut width = 1;
    while width < n {
        for low in (0..n).step_by(2 * width) {
            let middle = (low + width).min(n);
            let high = (low + 2 * width).min(n);
            let (mut left, mut right, mut out) = (low, middle, low);
            while left < middle {
                if right < high && nums[order[right]] < nums[order[left]] {
                    buffer[out] = order[right];
                    right += 1;
                } else {
                    // Every right-half element taken so far is smaller and came after it.
                    counts[order[left]] += (right - middle) as i32;
                    buffer[out] = order[left];
                    left += 1;
                }
                out += 1;
            }
            buffer[out..high].copy_from_slice(&order[right..high]);
        }
        std::mem::swap(&mut order, &mut buffer);
        width *= 2;
    }
    counts
}
