use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn is_balanced(root: Option<Rc<RefCell<TreeNode>>>) -> bool {
    checked_height(&root).is_some()
}

/// Height of `node`, or `None` as soon as any subtree below it is unbalanced.
fn checked_height(node: &Option<Rc<RefCell<TreeNode>>>) -> Option<i32> {
    let Some(node) = node else { return Some(0) };
    let node = node.borrow();
    let left = checked_height(&node.left)?;
    let right = checked_height(&node.right)?;
    if (left - right).abs() > 1 {
        return None;
    }
    Some(1 + left.max(right))
}
