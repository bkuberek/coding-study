use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn is_valid_bst(root: Option<Rc<RefCell<TreeNode>>>) -> bool {
    within(&root, None, None)
}

/// Is every value of the subtree strictly between `low` and `high` (`None`: unbounded)?
fn within(node: &Option<Rc<RefCell<TreeNode>>>, low: Option<i32>, high: Option<i32>) -> bool {
    let Some(node) = node else { return true };
    let node = node.borrow();
    if low.is_some_and(|low| node.val <= low) || high.is_some_and(|high| node.val >= high) {
        return false;
    }
    within(&node.left, low, Some(node.val)) && within(&node.right, Some(node.val), high)
}
