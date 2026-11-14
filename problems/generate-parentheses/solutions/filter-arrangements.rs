/// Whether the brackets are correctly nested. The depth is the height a stack of unmatched "("
/// would have.
fn is_balanced(brackets: &[char]) -> bool {
    let mut depth = 0;
    for &bracket in brackets {
        depth += if bracket == '(' { 1 } else { -1 };
        if depth < 0 {
            return false;
        }
    }
    depth == 0
}

pub fn generate_parenthesis(n: i32) -> Vec<String> {
    let n = n as usize;
    let size = 2 * n;
    let mut result = Vec::new();
    // `opening` holds the positions of the "(" characters in increasing order, starting with
    // 0..n; the loop steps through every choice of n positions out of 2n in lexicographic order.
    let mut opening: Vec<usize> = (0..n).collect();
    loop {
        let mut brackets = vec![')'; size];
        for &position in &opening {
            brackets[position] = '(';
        }
        if is_balanced(&brackets) {
            result.push(brackets.iter().collect());
        }
        // Advance the rightmost position that can still move right, and reset those after it.
        let Some(i) = (0..n).rev().find(|&i| opening[i] != size - n + i) else {
            return result;
        };
        opening[i] += 1;
        for j in i + 1..n {
            opening[j] = opening[j - 1] + 1;
        }
    }
}
