const MODULUS: i64 = 1_000_000_007;

pub fn create_sorted_array(instructions: Vec<i32>) -> i32 {
    let largest = instructions.iter().copied().max().unwrap_or(0) as usize;
    // tree[i] (1-based) counts the inserted values in (i - (i & -i), i].
    let mut tree = vec![0_i64; largest + 1];

    let count_at_most = |tree: &[i64], mut value: usize| {
        let mut total = 0;
        while value > 0 {
            total += tree[value];
            value -= value & value.wrapping_neg();
        }
        total
    };

    let mut cost = 0;
    for (inserted, &value) in instructions.iter().enumerate() {
        let value = value as usize;
        let less = count_at_most(&tree, value - 1);
        let greater = inserted as i64 - count_at_most(&tree, value);
        cost = (cost + less.min(greater)) % MODULUS;
        let mut position = value;
        while position <= largest {
            tree[position] += 1;
            position += position & position.wrapping_neg();
        }
    }
    cost as i32
}
