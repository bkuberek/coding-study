use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn is_subtree(
    root: Option<Rc<RefCell<TreeNode>>>,
    sub_root: Option<Rc<RefCell<TreeNode>>>,
) -> bool {
    occurs(&tokens(sub_root), &tokens(root))
}

/// Pre-order values with `None` for every missing child: a unique description of the tree.
fn tokens(root: Option<Rc<RefCell<TreeNode>>>) -> Vec<Option<i32>> {
    let mut tokens = Vec::new();
    let mut pending = vec![root];
    while let Some(entry) = pending.pop() {
        match entry {
            None => tokens.push(None),
            Some(node) => {
                let node = node.borrow();
                tokens.push(Some(node.val));
                pending.push(node.right.clone());
                pending.push(node.left.clone());
            }
        }
    }
    tokens
}

/// Knuth-Morris-Pratt: does `pattern` occur as a contiguous block of `text`?
fn occurs(pattern: &[Option<i32>], text: &[Option<i32>]) -> bool {
    let mut border = vec![0; pattern.len()];
    let mut length = 0;
    for i in 1..pattern.len() {
        while length > 0 && pattern[i] != pattern[length] {
            length = border[length - 1];
        }
        if pattern[i] == pattern[length] {
            length += 1;
        }
        border[i] = length;
    }
    let mut matched = 0;
    for token in text {
        while matched > 0 && *token != pattern[matched] {
            matched = border[matched - 1];
        }
        if *token == pattern[matched] {
            matched += 1;
            if matched == pattern.len() {
                return true;
            }
        }
    }
    false
}
