use std::cell::RefCell;
use std::collections::VecDeque;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn max_depth(root: Option<Rc<RefCell<TreeNode>>>) -> i32 {
    let mut level: VecDeque<Rc<RefCell<TreeNode>>> = root.into_iter().collect();
    let mut depth = 0;
    while !level.is_empty() {
        depth += 1;
        // Drain exactly the nodes of the current level; their children form the next one.
        for _ in 0..level.len() {
            let node = level.pop_front().expect("the level holds that many nodes");
            let node = node.borrow();
            level.extend(node.left.iter().cloned());
            level.extend(node.right.iter().cloned());
        }
    }
    depth
}
