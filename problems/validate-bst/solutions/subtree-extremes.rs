use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn is_valid_bst(root: Option<Rc<RefCell<TreeNode>>>) -> bool {
    valid(&root)
}

fn valid(root: &Option<Rc<RefCell<TreeNode>>>) -> bool {
    let Some(node) = root else { return true };
    let node = node.borrow();
    if largest(&node.left).is_some_and(|value| value >= node.val) {
        return false;
    }
    if smallest(&node.right).is_some_and(|value| value <= node.val) {
        return false;
    }
    valid(&node.left) && valid(&node.right)
}

/// Largest value anywhere in the subtree (`None` when it is empty); it need not be a search
/// tree, so scan it all.
fn largest(node: &Option<Rc<RefCell<TreeNode>>>) -> Option<i32> {
    let node = node.as_ref()?.borrow();
    let below = [&node.left, &node.right]
        .into_iter()
        .filter_map(largest)
        .max();
    Some(below.map_or(node.val, |value| value.max(node.val)))
}

fn smallest(node: &Option<Rc<RefCell<TreeNode>>>) -> Option<i32> {
    let node = node.as_ref()?.borrow();
    let below = [&node.left, &node.right]
        .into_iter()
        .filter_map(smallest)
        .min();
    Some(below.map_or(node.val, |value| value.min(node.val)))
}
