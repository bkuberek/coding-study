pub fn lamp_patterns(n: i32) -> Vec<String> {
    let mut result = Vec::new();
    let mut lamps = String::with_capacity(n as usize);
    extend(n as usize, &mut lamps, &mut result);
    result
}

fn extend(n: usize, lamps: &mut String, result: &mut Vec<String>) {
    if lamps.len() == n {
        result.push(lamps.clone());
        return;
    }
    // Choose "off", explore the lamps to the right, then undo the choice.
    lamps.push('0');
    extend(n, lamps, result);
    lamps.pop();
    // Prune: a lamp may be on only when its left neighbour is off (or missing).
    if !lamps.ends_with('1') {
        lamps.push('1');
        extend(n, lamps, result);
        lamps.pop();
    }
}
