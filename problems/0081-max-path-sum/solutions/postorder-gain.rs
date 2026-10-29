use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn max_path_sum(root: Option<Rc<RefCell<TreeNode>>>) -> i32 {
    let mut best = i32::MIN;
    gain(&root, &mut best);
    best
}

/// Best downward path sum from `node`, recording the best path turning at it in `best`.
fn gain(node: &Option<Rc<RefCell<TreeNode>>>, best: &mut i32) -> i32 {
    let Some(node) = node else { return 0 };
    let node = node.borrow();
    let left = gain(&node.left, best).max(0);
    let right = gain(&node.right, best).max(0);
    *best = (*best).max(node.val + left + right);
    node.val + left.max(right)
}
