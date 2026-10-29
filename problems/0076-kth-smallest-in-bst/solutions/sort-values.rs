use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn kth_smallest(root: Option<Rc<RefCell<TreeNode>>>, k: i32) -> i32 {
    let mut values = Vec::new();
    let mut pending = vec![root];
    while let Some(entry) = pending.pop() {
        if let Some(node) = entry {
            let node = node.borrow();
            values.push(node.val);
            pending.push(node.left.clone());
            pending.push(node.right.clone());
        }
    }
    values.sort_unstable();
    values[k as usize - 1]
}
