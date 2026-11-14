use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn diameter_of_binary_tree(root: Option<Rc<RefCell<TreeNode>>>) -> i32 {
    let mut best = 0;
    height(&root, &mut best);
    best
}

/// Returns the height of `node` and raises `best` to the longest path that turns at a node.
fn height(node: &Option<Rc<RefCell<TreeNode>>>, best: &mut i32) -> i32 {
    let Some(node) = node else { return 0 };
    let node = node.borrow();
    let (left, right) = (height(&node.left, best), height(&node.right, best));
    *best = (*best).max(left + right);
    1 + left.max(right)
}
