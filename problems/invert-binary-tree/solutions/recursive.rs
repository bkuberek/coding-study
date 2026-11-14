use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn invert_tree(root: Option<Rc<RefCell<TreeNode>>>) -> Option<Rc<RefCell<TreeNode>>> {
    if let Some(node) = &root {
        let mut node = node.borrow_mut();
        let left = invert_tree(node.left.take());
        let right = invert_tree(node.right.take());
        node.left = right;
        node.right = left;
    }
    root
}
