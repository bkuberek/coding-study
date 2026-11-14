use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn max_depth(root: Option<Rc<RefCell<TreeNode>>>) -> i32 {
    depth(&root)
}

fn depth(node: &Option<Rc<RefCell<TreeNode>>>) -> i32 {
    match node {
        None => 0,
        Some(node) => {
            let node = node.borrow();
            1 + depth(&node.left).max(depth(&node.right))
        }
    }
}
