use std::cell::RefCell;
use std::rc::Rc;

use cs_support::TreeNode;

pub fn path_sum(root: Option<Rc<RefCell<TreeNode>>>, target_sum: i32) -> i32 {
    let mut count = 0;
    let mut starts: Vec<Rc<RefCell<TreeNode>>> = root.into_iter().collect();
    while let Some(start) = starts.pop() {
        // Walk every downward path from start, carrying the sum so far.
        let mut pending = vec![(Rc::clone(&start), start.borrow().val)];
        while let Some((node, total)) = pending.pop() {
            if total == target_sum {
                count += 1;
            }
            let node = node.borrow();
            for child in [&node.left, &node.right].into_iter().flatten() {
                let child_total = total + child.borrow().val;
                pending.push((Rc::clone(child), child_total));
            }
        }
        let start = start.borrow();
        starts.extend([&start.left, &start.right].into_iter().flatten().cloned());
    }
    count
}
