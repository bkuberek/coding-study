use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn level_order(root: Option<Rc<RefCell<TreeNode>>>) -> Vec<Vec<i32>> {
    let mut levels: Vec<Vec<i32>> = Vec::new();
    // Pre-order with an explicit stack; pushing right before left visits left first.
    let mut pending: Vec<(Rc<RefCell<TreeNode>>, usize)> =
        root.into_iter().map(|node| (node, 0)).collect();
    while let Some((node, depth)) = pending.pop() {
        if depth == levels.len() {
            levels.push(Vec::new());
        }
        let node = node.borrow();
        levels[depth].push(node.val);
        pending.extend(node.right.iter().map(|right| (Rc::clone(right), depth + 1)));
        pending.extend(node.left.iter().map(|left| (Rc::clone(left), depth + 1)));
    }
    levels
}
