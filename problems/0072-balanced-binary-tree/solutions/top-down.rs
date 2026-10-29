use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn is_balanced(root: Option<Rc<RefCell<TreeNode>>>) -> bool {
    balanced(&root)
}

fn balanced(root: &Option<Rc<RefCell<TreeNode>>>) -> bool {
    let Some(node) = root else { return true };
    let node = node.borrow();
    (height(&node.left) - height(&node.right)).abs() <= 1
        && balanced(&node.left)
        && balanced(&node.right)
}

fn height(node: &Option<Rc<RefCell<TreeNode>>>) -> i32 {
    match node {
        None => 0,
        Some(node) => {
            let node = node.borrow();
            1 + height(&node.left).max(height(&node.right))
        }
    }
}
