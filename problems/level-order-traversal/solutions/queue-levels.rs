use std::cell::RefCell;
use std::collections::VecDeque;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn level_order(root: Option<Rc<RefCell<TreeNode>>>) -> Vec<Vec<i32>> {
    let mut levels = Vec::new();
    let mut queue: VecDeque<Rc<RefCell<TreeNode>>> = root.into_iter().collect();
    while !queue.is_empty() {
        let mut level = Vec::with_capacity(queue.len());
        for _ in 0..queue.len() {
            let node = queue.pop_front().expect("the level holds that many nodes");
            let node = node.borrow();
            level.push(node.val);
            queue.extend(node.left.iter().cloned());
            queue.extend(node.right.iter().cloned());
        }
        levels.push(level);
    }
    levels
}
