use std::cell::RefCell;
use std::collections::VecDeque;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn invert_tree(root: Option<Rc<RefCell<TreeNode>>>) -> Option<Rc<RefCell<TreeNode>>> {
    let mut pending: VecDeque<Rc<RefCell<TreeNode>>> = root.iter().cloned().collect();
    while let Some(node) = pending.pop_front() {
        let mut guard = node.borrow_mut();
        let node = &mut *guard;
        std::mem::swap(&mut node.left, &mut node.right);
        pending.extend(node.left.iter().chain(node.right.iter()).cloned());
    }
    root
}
