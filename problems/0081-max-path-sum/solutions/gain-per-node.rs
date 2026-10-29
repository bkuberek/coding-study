use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn max_path_sum(root: Option<Rc<RefCell<TreeNode>>>) -> i32 {
    best_path(&root).expect("the tree has at least one node")
}

/// The best path anywhere in the subtree (`None` when it is empty): the best one turning at
/// `node` itself, or the best one inside either child.
fn best_path(node: &Option<Rc<RefCell<TreeNode>>>) -> Option<i32> {
    let node = node.as_ref()?.borrow();
    let turning_here = node.val + gain(&node.left).max(0) + gain(&node.right).max(0);
    Some(
        [best_path(&node.left), best_path(&node.right)]
            .into_iter()
            .flatten()
            .fold(turning_here, i32::max),
    )
}

/// Largest sum of a path that starts at `node` and only goes down (0 for no node).
fn gain(node: &Option<Rc<RefCell<TreeNode>>>) -> i32 {
    match node {
        None => 0,
        Some(node) => {
            let node = node.borrow();
            node.val + gain(&node.left).max(gain(&node.right)).max(0)
        }
    }
}
