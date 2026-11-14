use std::cell::RefCell;
use std::collections::{HashMap, VecDeque};
use std::rc::Rc;

use cs_support::TreeNode;

pub fn vertical_order(root: Option<Rc<RefCell<TreeNode>>>) -> Vec<Vec<i32>> {
    let Some(root) = root else {
        return Vec::new();
    };
    let mut columns: HashMap<i32, Vec<i32>> = HashMap::new();
    let (mut lowest, mut highest) = (0, 0);
    let mut queue = VecDeque::from([(root, 0)]);
    while let Some((node, column)) = queue.pop_front() {
        let node = node.borrow();
        columns.entry(column).or_default().push(node.val);
        (lowest, highest) = (lowest.min(column), highest.max(column));
        if let Some(left) = &node.left {
            queue.push_back((Rc::clone(left), column - 1));
        }
        if let Some(right) = &node.right {
            queue.push_back((Rc::clone(right), column + 1));
        }
    }
    // Columns form a contiguous range: every path from the root moves one column per step.
    (lowest..=highest)
        .map(|column| columns.remove(&column).expect("columns are contiguous"))
        .collect()
}
