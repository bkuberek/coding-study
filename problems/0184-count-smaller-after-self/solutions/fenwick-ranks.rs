/// The lowest set bit of `i`. `usize` has no unary minus, so `-i` is spelled `wrapping_neg`.
fn low_bit(i: usize) -> usize {
    i & i.wrapping_neg()
}

pub fn count_smaller(nums: Vec<i32>) -> Vec<i32> {
    // Coordinate compression: rank 1 is the smallest distinct value.
    let mut distinct = nums.clone();
    distinct.sort_unstable();
    distinct.dedup();
    let size = distinct.len();
    let mut tree = vec![0; size + 1]; // Fenwick tree: how many seen values have each rank
    let mut counts = vec![0; nums.len()];
    for (i, value) in nums.iter().enumerate().rev() {
        let mut rank = distinct
            .binary_search(value)
            .expect("every value is in the sorted distinct list")
            + 1;
        // Seen values with a rank below `rank`, i.e. strictly smaller values to the right.
        let mut smaller = 0;
        let mut j = rank - 1;
        while j > 0 {
            smaller += tree[j];
            j -= low_bit(j);
        }
        counts[i] = smaller;
        while rank <= size {
            tree[rank] += 1;
            rank += low_bit(rank);
        }
    }
    counts
}
