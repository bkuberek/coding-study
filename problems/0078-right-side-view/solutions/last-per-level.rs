use std::cell::RefCell;
use std::collections::VecDeque;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn right_side_view(root: Option<Rc<RefCell<TreeNode>>>) -> Vec<i32> {
    let mut view = Vec::new();
    let mut queue: VecDeque<Rc<RefCell<TreeNode>>> = root.into_iter().collect();
    // The node at the back of the queue is the last one of the current level.
    while let Some(last) = queue.back() {
        view.push(last.borrow().val);
        for _ in 0..queue.len() {
            let node = queue.pop_front().expect("the level holds that many nodes");
            let node = node.borrow();
            queue.extend(node.left.iter().cloned());
            queue.extend(node.right.iter().cloned());
        }
    }
    view
}
