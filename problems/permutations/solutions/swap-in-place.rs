pub fn permute(nums: Vec<i32>) -> Vec<Vec<i32>> {
    let mut values = nums;
    let mut result = Vec::new();
    fix_slot(&mut values, 0, &mut result);
    result
}

/// `values[..slot]` is the fixed prefix; `values[slot..]` are the candidates still free.
fn fix_slot(values: &mut [i32], slot: usize, result: &mut Vec<Vec<i32>>) {
    if slot == values.len() {
        result.push(values.to_vec());
        return;
    }
    for candidate in slot..values.len() {
        values.swap(slot, candidate);
        fix_slot(values, slot + 1, result);
        values.swap(slot, candidate);
    }
}
