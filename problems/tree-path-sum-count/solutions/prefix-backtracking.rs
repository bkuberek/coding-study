use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

use cs_support::TreeNode;

type Link = Option<Rc<RefCell<TreeNode>>>;

/// Counts the paths below `node` that end at a node and sum to the target; `on_path` counts the
/// prefixes of the current root path by sum.
fn count_below(node: &Link, total: i32, target_sum: i32, on_path: &mut HashMap<i32, i32>) -> i32 {
    let Some(node) = node else {
        return 0;
    };
    let node = node.borrow();
    let total = total + node.val;
    let mut found = on_path.get(&(total - target_sum)).copied().unwrap_or(0);
    *on_path.entry(total).or_insert(0) += 1;
    found += count_below(&node.left, total, target_sum, on_path);
    found += count_below(&node.right, total, target_sum, on_path);
    // Leave the subtree: its prefix is no longer on the path.
    if let Some(prefixes) = on_path.get_mut(&total) {
        *prefixes -= 1;
    }
    found
}

pub fn path_sum(root: Option<Rc<RefCell<TreeNode>>>, target_sum: i32) -> i32 {
    let mut on_path = HashMap::from([(0, 1)]);
    count_below(&root, 0, target_sum, &mut on_path)
}
