pub fn length_of_lis(nums: Vec<i32>) -> i32 {
    // tails[L - 1] is the smallest last value of any increasing subsequence of length L seen
    // so far; it is strictly increasing, so it can be binary searched.
    let mut tails: Vec<i32> = Vec::with_capacity(nums.len());
    for value in nums {
        // The first position whose tail is not smaller than `value`.
        let position = tails.partition_point(|&tail| tail < value);
        if position == tails.len() {
            tails.push(value);
        } else {
            tails[position] = value;
        }
    }
    tails.len() as i32
}
