use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn diameter_of_binary_tree(root: Option<Rc<RefCell<TreeNode>>>) -> i32 {
    diameter(&root)
}

fn diameter(root: &Option<Rc<RefCell<TreeNode>>>) -> i32 {
    let Some(node) = root else { return 0 };
    let node = node.borrow();
    let turning_here = height(&node.left) + height(&node.right);
    turning_here
        .max(diameter(&node.left))
        .max(diameter(&node.right))
}

/// Number of nodes on the longest downward path from `node`.
fn height(node: &Option<Rc<RefCell<TreeNode>>>) -> i32 {
    match node {
        None => 0,
        Some(node) => {
            let node = node.borrow();
            1 + height(&node.left).max(height(&node.right))
        }
    }
}
