const MODULUS: i64 = 1_000_000_007;

pub fn create_sorted_array(instructions: Vec<i32>) -> i32 {
    let mut ordered: Vec<i32> = Vec::with_capacity(instructions.len());
    let mut cost: i64 = 0;
    for value in instructions {
        let less = ordered.partition_point(|&other| other < value);
        let at_most = ordered.partition_point(|&other| other <= value);
        let greater = ordered.len() - at_most;
        cost += less.min(greater) as i64;
        ordered.insert(at_most, value);
    }
    (cost % MODULUS) as i32
}
